"""Milestone 8: End-to-End Multi-Language Integration and Security Hardening Tests."""
import uuid
import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.analyzer.orchestrator import AnalysisOrchestrator
from src.core.config import settings
from src.core.errors import ErrorCode, PatchwiseAPIException
from src.github.client import GitHubClient, parse_github_repo_and_number
from src.github.mock import MockGitHubClient
from src.github.models import GitHubChangedFile, GitHubPullRequest
from src.main import app
from src.providers.base import CandidateFinding
from src.providers.rule_only import RuleOnlyProvider
from src.routers.reviews import get_github_client
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity
from src.schemas.reviews import ReviewStatus


# Multi-language diff patch fixtures
SAMPLE_PY_PATCH = "@@ -1,3 +1,4 @@\n def f():\n-    pass\n+    eval('user_input')\n"
SAMPLE_TS_PATCH = "@@ -1,3 +1,4 @@\n function run() {\n-  return;\n+  eval(userCmd);\n}\n"
SAMPLE_JAVA_PATCH = "@@ -1,3 +1,4 @@\n public void read(InputStream is) {\n-  return;\n+  new ObjectInputStream(is).readObject();\n}\n"
SAMPLE_CPP_PATCH = "@@ -1,3 +1,4 @@\n void process(char* in) {\n-  return;\n+  strcpy(buf, in);\n}\n"
SAMPLE_SQL_PATCH = "@@ -1,3 +1,4 @@\n -- migration script\n-SELECT 1;\n+UPDATE users SET active = 0;\n"


@pytest.mark.asyncio
async def test_multi_language_pull_request_end_to_end(db_session: AsyncSession):
    """
    Verifies that a single pull request containing Python, TypeScript, Java, C++,
    and SQL files is dispatched to all 5 analyzers, producing Tier 1 findings with
    accurate line grounding for every language.
    """
    multi_lang_files = [
        GitHubChangedFile(filename="src/backend.py", status="modified", patch=SAMPLE_PY_PATCH),
        GitHubChangedFile(filename="src/frontend.ts", status="modified", patch=SAMPLE_TS_PATCH),
        GitHubChangedFile(filename="src/Service.java", status="modified", patch=SAMPLE_JAVA_PATCH),
        GitHubChangedFile(filename="src/driver.cpp", status="modified", patch=SAMPLE_CPP_PATCH),
        GitHubChangedFile(filename="db/migration.sql", status="modified", patch=SAMPLE_SQL_PATCH),
    ]

    gh_client = MockGitHubClient(sample_files=multi_lang_files)
    orchestrator = AnalysisOrchestrator(db=db_session, github_client=gh_client)

    review = await orchestrator.run_review("https://github.com/org/multi-lang-project", 100)

    assert review.status == ReviewStatus.COMPLETED
    assert review.summary.deterministic_count >= 5

    # Check rule IDs across languages are all present
    rule_ids = {f.rule_id for f in review.findings}
    assert "PY004" in rule_ids   # Python eval
    assert "JS001" in rule_ids   # TypeScript eval
    assert "JV001" in rule_ids   # Java readObject
    assert "CC001" in rule_ids   # C++ strcpy
    assert "SQL001" in rule_ids  # SQL unbounded UPDATE

    # Verify all findings have strictly Tier 1 provenance and valid grounded lines
    for f in review.findings:
        assert f.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
        assert f.start_line is not None and f.start_line > 0


@pytest.mark.asyncio
async def test_end_to_end_handles_heterogeneous_non_code_files(db_session: AsyncSession):
    """
    Verifies that deleted, renamed, binary, empty, and non-supported files
    are processed without false positives or exceptions.
    """
    heterogeneous_files = [
        GitHubChangedFile(filename="src/clean.py", status="modified", patch="@@ -1,2 +1,3 @@\n def f():\n+    x = 1\n"),
        GitHubChangedFile(filename="assets/image.png", status="added", patch=None),
        GitHubChangedFile(filename="docs/README.md", status="modified", patch="@@ -1,1 +1,2 @@\n+# Doc\n"),
        GitHubChangedFile(filename="legacy/old.py", status="removed", patch="@@ -1,3 +0,0 @@\n-def old():\n-    pass\n"),
        GitHubChangedFile(filename="src/empty.ts", status="modified", patch=""),
    ]

    gh_client = MockGitHubClient(sample_files=heterogeneous_files)
    orchestrator = AnalysisOrchestrator(db=db_session, github_client=gh_client)

    review = await orchestrator.run_review("https://github.com/org/mixed-repo", 101)

    assert review.status == ReviewStatus.COMPLETED
    # Clean file changes should produce zero false positives
    security_findings = [f for f in review.findings if f.category != FindingCategory.TEST_SUGGESTION]
    assert len(security_findings) == 0


def test_strict_https_url_validation():
    """Verifies that insecure HTTP, path traversal, and SSRF URLs are rejected."""
    # Disallow cleartext HTTP
    with pytest.raises(PatchwiseAPIException) as exc:
        parse_github_repo_and_number("http://github.com/owner/repo/pull/1")
    assert exc.value.error_code == ErrorCode.INVALID_REPOSITORY_URL
    assert "insecure http" in exc.value.message.lower()

    # Disallow path traversal sequences
    with pytest.raises(PatchwiseAPIException) as exc:
        parse_github_repo_and_number("https://github.com/../repo/pull/1")
    assert exc.value.error_code == ErrorCode.INVALID_REPOSITORY_URL
    assert "traversal" in exc.value.message.lower()

    with pytest.raises(PatchwiseAPIException) as exc:
        parse_github_repo_and_number("https://github.com/owner/../pull/1")
    assert exc.value.error_code == ErrorCode.INVALID_REPOSITORY_URL

    # Disallow PR number 0 or negative
    with pytest.raises(PatchwiseAPIException) as exc:
        parse_github_repo_and_number("https://github.com/owner/repo/pull/0")
    assert exc.value.error_code == ErrorCode.INVALID_REPOSITORY_URL

    # Valid PR URL parses successfully
    owner, repo, num = parse_github_repo_and_number("https://github.com/owner/repo/pull/42")
    assert owner == "owner"
    assert repo == "repo"
    assert num == 42


@pytest.mark.asyncio
async def test_request_size_limit_middleware(client: AsyncClient, monkeypatch):
    """Verifies that payloads exceeding MAX_REQUEST_BODY_BYTES return HTTP 413."""
    # Set limit to 100 bytes for test
    from src.main import RequestSizeLimitMiddleware
    # Send request with oversized Content-Length
    headers = {"Content-Length": "5000000", "Content-Type": "application/json"}
    res = await client.post(
        "/api/v1/reviews",
        content=b"{}",
        headers=headers,
    )
    assert res.status_code == 413
    data = res.json()
    assert data["error"]["code"] == "REQUEST_ENTITY_TOO_LARGE"


@pytest.mark.asyncio
async def test_orchestrator_defense_in_depth_line_grounding(db_session: AsyncSession):
    """
    Verifies that the orchestrator boundary gate discards any ungrounded findings
    even if injected by a faulty provider.
    """
    gh_client = MockGitHubClient()

    class FaultyProvider(RuleOnlyProvider):
        async def review(self, context):
            res = await super().review(context)
            # Inject an ungrounded finding targeting line 99999
            ungrounded = CandidateFinding(
                rule_id="HALLUCINATED_RULE",
                severity=FindingSeverity.HIGH,
                category=FindingCategory.SECURITY_PATTERN,
                file_path="src/calculator.py",
                start_line=99999,
                end_line=99999,
                title="Hallucinated Bug",
                explanation="Non-existent line",
                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
            )
            res.findings.append(ungrounded)
            return res

    orchestrator = AnalysisOrchestrator(
        db=db_session,
        github_client=gh_client,
        rule_provider=FaultyProvider(),
    )

    review = await orchestrator.run_review("https://github.com/my-org/backend-service", 99)

    # The ungrounded candidate targeting line 99999 must NOT be in final review findings
    assert not any(f.rule_id == "HALLUCINATED_RULE" for f in review.findings)
    assert not any(f.start_line == 99999 for f in review.findings)


@pytest.mark.asyncio
async def test_api_key_authentication_enforcement(client: AsyncClient, monkeypatch):
    """
    Verifies that when API_SECRET_KEY is configured:
    - Unauthenticated requests are rejected with 401.
    - Requests with valid X-API-Key or Authorization Bearer header pass.
    """
    monkeypatch.setattr(settings, "API_SECRET_KEY", "test-secret-key-12345")
    mock_gh = MockGitHubClient()
    app.dependency_overrides[get_github_client] = lambda: mock_gh

    try:
        # 1. Unauthenticated request -> 401
        res_unauth = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/1"},
        )
        assert res_unauth.status_code == 401
        assert "unauthorized" in res_unauth.json()["error"]["message"].lower()

        # 2. Invalid API key -> 401
        res_invalid = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/1"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert res_invalid.status_code == 401

        # 3. Valid X-API-Key -> 200
        res_valid_x = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/1"},
            headers={"X-API-Key": "test-secret-key-12345"},
        )
        assert res_valid_x.status_code == 200

        # 4. Valid Authorization Bearer -> 200
        res_valid_bearer = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/1"},
            headers={"Authorization": "Bearer test-secret-key-12345"},
        )
        assert res_valid_bearer.status_code == 200

    finally:
        app.dependency_overrides.pop(get_github_client, None)


@pytest.mark.asyncio
async def test_pr_url_without_separate_pr_number_succeeds(client: AsyncClient):
    """Verifies that submitting a full PR URL parses pull_request_number directly."""
    mock_gh = MockGitHubClient()
    app.dependency_overrides[get_github_client] = lambda: mock_gh

    try:
        res = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/77"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["pr_number"] == 77
        assert data["repository"] == "owner/repo"
    finally:
        app.dependency_overrides.pop(get_github_client, None)


@pytest.mark.asyncio
async def test_authentication_fail_closed_in_production(client: AsyncClient, monkeypatch):
    """
    Verifies that when ENVIRONMENT is 'production':
    - If API_SECRET_KEY is empty or None, requests FAIL CLOSED (401 Unauthorized).
    - If API_SECRET_KEY is configured, valid keys succeed, invalid/missing keys return 401.
    """
    mock_gh = MockGitHubClient()
    app.dependency_overrides[get_github_client] = lambda: mock_gh

    try:
        # Case A: Production with NO API_SECRET_KEY -> must fail closed
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "API_SECRET_KEY", None)

        res_no_key = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/1"},
        )
        assert res_no_key.status_code == 401
        assert "api_secret_key must be configured" in res_no_key.json()["error"]["message"].lower()

        # Case B: Production with empty string API_SECRET_KEY -> must fail closed
        monkeypatch.setattr(settings, "API_SECRET_KEY", "   ")
        res_blank_key = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/1"},
        )
        assert res_blank_key.status_code == 401

        # Case C: Production with valid key configured
        monkeypatch.setattr(settings, "API_SECRET_KEY", "prod-secret-key-999")
        # Missing key -> 401
        res_missing = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/1"},
        )
        assert res_missing.status_code == 401

        # Invalid key -> 401
        res_bad = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/1"},
            headers={"X-API-Key": "wrong-secret"},
        )
        assert res_bad.status_code == 401

        # Valid key -> 200
        res_ok = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/1"},
            headers={"X-API-Key": "prod-secret-key-999"},
        )
        assert res_ok.status_code == 200

    finally:
        app.dependency_overrides.pop(get_github_client, None)


@pytest.mark.asyncio
async def test_authentication_development_mode_permissive(client: AsyncClient, monkeypatch):
    """Verifies that in local development with no key configured, requests pass without credentials."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "API_SECRET_KEY", None)
    mock_gh = MockGitHubClient()
    app.dependency_overrides[get_github_client] = lambda: mock_gh

    try:
        res = await client.post(
            "/api/v1/reviews/inspect",
            json={"repository_url": "https://github.com/owner/repo/pull/1"},
        )
        assert res.status_code == 200
    finally:
        app.dependency_overrides.pop(get_github_client, None)


@pytest.mark.asyncio
async def test_feedback_endpoint_authentication_enforcement(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """Verifies that feedback submission on findings enforces API key authentication."""
    from datetime import datetime, timezone
    from src.db.models import Finding, Review

    monkeypatch.setattr(settings, "API_SECRET_KEY", "feedback-auth-secret")

    # Seed test review and finding
    r_id = uuid.uuid4()
    f_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    review = Review(
        id=r_id,
        repository="test-org/repo",
        pr_number=5,
        status="completed",
        engine_version="0.1.0",
        started_at=now,
    )
    finding = Finding(
        id=f_id,
        review_id=r_id,
        rule_id="PY001",
        source="DETERMINISTIC_STATIC_ANALYSIS",
        severity="high",
        category="input_validation",
        file_path="app.py",
        title="Unvalidated input",
        explanation="Missing validation",
        created_at=now,
    )
    db_session.add(review)
    db_session.add(finding)
    await db_session.commit()

    feedback_payload = {"verdict": "useful", "comment": "Good catch"}

    # 1. Unauthenticated -> 401
    res_unauth = await client.post(
        f"/api/v1/reviews/{r_id}/findings/{f_id}/feedback",
        json=feedback_payload,
    )
    assert res_unauth.status_code == 401

    # 2. Invalid key -> 401
    res_bad = await client.post(
        f"/api/v1/reviews/{r_id}/findings/{f_id}/feedback",
        json=feedback_payload,
        headers={"X-API-Key": "incorrect-secret"},
    )
    assert res_bad.status_code == 401

    # 3. Valid key -> 201 Created
    res_ok = await client.post(
        f"/api/v1/reviews/{r_id}/findings/{f_id}/feedback",
        json=feedback_payload,
        headers={"X-API-Key": "feedback-auth-secret"},
    )
    assert res_ok.status_code == 201
    data = res_ok.json()
    assert data["verdict"] == "useful"
    assert data["comment"] == "Good catch"


@pytest.mark.asyncio
async def test_public_read_endpoints_accessible_without_auth(client: AsyncClient, monkeypatch):
    """
    Verifies that public monitoring and read-only dashboard endpoints
    remain accessible without authentication even when API_SECRET_KEY is set.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "API_SECRET_KEY", "mandatory-prod-secret")

    # Health endpoints
    res_health = await client.get("/health")
    assert res_health.status_code == 200

    res_v1_health = await client.get("/api/v1/health")
    assert res_v1_health.status_code == 200

    # Review listing (read-only)
    res_reviews = await client.get("/api/v1/reviews")
    assert res_reviews.status_code == 200

    # Benchmarks (read-only)
    res_benchmarks = await client.get("/api/v1/benchmarks")
    assert res_benchmarks.status_code == 200

    # Plugins overview (read-only)
    res_plugins = await client.get("/api/v1/plugins")
    assert res_plugins.status_code == 200


@pytest.mark.asyncio
async def test_production_lifespan_startup_rejection(monkeypatch):
    """Verifies that lifespan startup hook refuses to boot in production if API_SECRET_KEY is unset."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "API_SECRET_KEY", None)

    from src.main import lifespan

    with pytest.raises(RuntimeError) as exc_info:
        async with lifespan(app):
            pass

    assert "api_secret_key must be configured" in str(exc_info.value).lower()
    assert "refusing to start" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_request_size_middleware_malformed_headers(client: AsyncClient):
    """Verifies that malformed and negative Content-Length headers return HTTP 400."""
    # Negative Content-Length
    res_neg = await client.post(
        "/api/v1/reviews",
        content=b"{}",
        headers={"Content-Length": "-100", "Content-Type": "application/json"},
    )
    assert res_neg.status_code == 400
    assert "invalid negative" in res_neg.json()["error"]["message"].lower()

    # Non-integer Content-Length
    res_nan = await client.post(
        "/api/v1/reviews",
        content=b"{}",
        headers={"Content-Length": "not-a-number", "Content-Type": "application/json"},
    )
    assert res_nan.status_code == 400
    assert "malformed" in res_nan.json()["error"]["message"].lower()


def test_strict_github_url_security_rejections():
    """Verifies rejection of embedded credentials, query strings, fragments, and illegal hosts."""
    # Embedded credentials
    with pytest.raises(PatchwiseAPIException) as exc:
        parse_github_repo_and_number("https://user:password@github.com/owner/repo/pull/1")
    assert exc.value.error_code == ErrorCode.INVALID_REPOSITORY_URL
    assert "user credentials" in exc.value.message.lower()

    # Query parameters
    with pytest.raises(PatchwiseAPIException) as exc:
        parse_github_repo_and_number("https://github.com/owner/repo/pull/1?filter=unreviewed")
    assert exc.value.error_code == ErrorCode.INVALID_REPOSITORY_URL
    assert "query parameters" in exc.value.message.lower()

    # URL fragments
    with pytest.raises(PatchwiseAPIException) as exc:
        parse_github_repo_and_number("https://github.com/owner/repo/pull/1#discussion_r123")
    assert exc.value.error_code == ErrorCode.INVALID_REPOSITORY_URL
    assert "fragments" in exc.value.message.lower()

    # URL-encoded traversal
    with pytest.raises(PatchwiseAPIException) as exc:
        parse_github_repo_and_number("https://github.com/%2e%2e/repo/pull/1")
    assert exc.value.error_code == ErrorCode.INVALID_REPOSITORY_URL
    assert "illegal url-encoded" in exc.value.message.lower()

    # Non-GitHub host
    with pytest.raises(PatchwiseAPIException) as exc:
        parse_github_repo_and_number("https://gitlab.com/owner/repo/pull/1")
    assert exc.value.error_code == ErrorCode.INVALID_REPOSITORY_URL
    assert "unsupported repository host" in exc.value.message.lower()

    # Invalid owner with leading hyphen
    with pytest.raises(PatchwiseAPIException) as exc:
        parse_github_repo_and_number("https://github.com/-invalid-owner/repo/pull/1")
    assert exc.value.error_code == ErrorCode.INVALID_REPOSITORY_URL


@pytest.mark.asyncio
async def test_github_client_redirect_defense():
    """Verifies that GitHubClient refuses redirects to external hosts to prevent credential leakage."""
    redirect_response = httpx.Response(
        status_code=302,
        headers={"Location": "https://evil-third-party.com/api/steal"},
        request=httpx.Request("GET", "https://api.github.com/repos/owner/repo/pulls/1"),
    )

    mock_transport = httpx.MockTransport(lambda req: redirect_response)
    async with httpx.AsyncClient(transport=mock_transport) as mock_http:
        client = GitHubClient(token="secret-gh-token", http_client=mock_http)
        with pytest.raises(PatchwiseAPIException) as exc:
            await client.get_pull_request("owner", "repo", 1)
        assert exc.value.error_code == ErrorCode.INTERNAL_ERROR
        assert "refusing redirect" in exc.value.message.lower()
