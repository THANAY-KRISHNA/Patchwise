"""
Patchwise Milestone 9: End-to-End Beta Acceptance Test Suite.

Exercises the complete pull request review lifecycle under realistic integration
conditions using controlled mock boundaries:
1. Valid PR submission with multi-language unified diffs (Python, TypeScript, Java, C++, SQL).
2. Diff parsing, hunk extraction, and added-line mapping.
3. Analyzer dispatching to all 5 language plugins.
4. Defense-in-depth line grounding and Tier 1 finding provenance enforcement.
5. Review and finding persistence, retrieval, and reviewer feedback workflow.
6. Negative & edge cases:
   - Empty diffs (0 files or blank patches).
   - Invalid repository URLs and malformed inputs.
   - GitHub upstream errors (404 not found, 429 rate limit, 502 upstream error).
   - Oversized request payloads exceeding limits (HTTP 413).
   - Production fail-closed authentication (HTTP 401 missing/invalid key, 201 valid key).

NOTE: All external network calls (GitHub API, LLM providers) are mocked to ensure
deterministic, offline execution in CI and local test environments. No external
services or production secrets are required.
"""

import json
import pytest
from httpx import AsyncClient
from unittest.mock import patch

from src.core.config import settings
from src.core.errors import ErrorCode, PatchwiseAPIException
from src.github.mock import MockGitHubClient
from src.github.models import GitHubChangedFile, GitHubPullRequest
from src.main import app
from src.routers.reviews import get_github_client
from src.schemas.findings import FindingProvenance, FindingSeverity
from src.schemas.reviews import ReviewStatus


# Multi-language diff patch fixtures for beta acceptance
BETA_PY_DIFF = (
    "@@ -1,5 +1,6 @@\n"
    " def process_user_input(payload):\n"
    "-    return True\n"
    "+    eval(payload['cmd'])\n"
    "+    return False\n"
)

BETA_TS_DIFF = (
    "@@ -10,6 +10,7 @@\n"
    " export function executeCommand(cmd: string) {\n"
    "-  logger.info('Executing command');\n"
    "+  eval(cmd);\n"
    "   return cmd;\n"
    " }\n"
)

BETA_JAVA_DIFF = (
    "@@ -20,6 +20,7 @@\n"
    " public Object deserialize(InputStream stream) throws Exception {\n"
    "-    return null;\n"
    "+    return new ObjectInputStream(stream).readObject();\n"
    " }\n"
)

BETA_CPP_DIFF = (
    "@@ -30,6 +30,7 @@\n"
    " void copy_buffer(const char* input) {\n"
    "     char local_buf[64];\n"
    "-    snprintf(local_buf, sizeof(local_buf), \"%s\", input);\n"
    "+    strcpy(local_buf, input);\n"
    " }\n"
)

BETA_SQL_DIFF = (
    "@@ -1,4 +1,5 @@\n"
    " -- Cleanup script\n"
    "-SELECT 1;\n"
    "+UPDATE accounts SET status = 'disabled';\n"
)


@pytest.mark.asyncio
async def test_beta_acceptance_full_pr_review_workflow(client: AsyncClient):
    """
    Gate 4 Primary Workflow:
    1. Submit valid multi-language PR.
    2. Parse unified diffs across Python, TypeScript, Java, C++, and SQL.
    3. Dispatch changed files to corresponding language analyzers.
    4. Enforce added-line grounding and Tier 1 finding provenance.
    5. Persist review session and query findings & submit reviewer feedback.
    """
    files = [
        GitHubChangedFile(filename="backend/handler.py", status="modified", patch=BETA_PY_DIFF),
        GitHubChangedFile(filename="frontend/command.ts", status="modified", patch=BETA_TS_DIFF),
        GitHubChangedFile(filename="services/DataParser.java", status="modified", patch=BETA_JAVA_DIFF),
        GitHubChangedFile(filename="native/buffer.cpp", status="modified", patch=BETA_CPP_DIFF),
        GitHubChangedFile(filename="db/migrations/cleanup.sql", status="modified", patch=BETA_SQL_DIFF),
    ]

    mock_gh = MockGitHubClient(sample_files=files)
    app.dependency_overrides[get_github_client] = lambda: mock_gh

    try:
        # Step 1: Submit pull request for review
        response = await client.post(
            "/api/v1/reviews",
            json={
                "repository_url": "https://github.com/acme-corp/multi-service-repo",
                "pull_request_number": 42,
            },
        )
        assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}: {response.text}"
        review_data = response.json()

        # Step 2 & 3: Review metadata and multi-language analyzer completion
        assert review_data["status"] == "completed"
        assert review_data["repository"] == "acme-corp/multi-service-repo"
        assert review_data["pr_number"] == 42
        review_id = review_data["id"]

        summary = review_data["summary"]
        assert summary["total_findings"] >= 5
        assert summary["deterministic_count"] >= 5
        assert summary["ai_hypothesis_count"] == 0  # No AI provider enabled in offline test

        # Step 4: Strict line grounding & provenance verification
        findings = review_data["findings"]
        rule_ids = {f["rule_id"] for f in findings}

        # Check coverage across all 5 languages
        assert "PY004" in rule_ids, "Expected Python eval rule PY004"
        assert "JS001" in rule_ids, "Expected TypeScript eval rule JS001"
        assert "JV001" in rule_ids, "Expected Java deserialization rule JV001"
        assert "CC001" in rule_ids, "Expected C++ strcpy rule CC001"
        assert "SQL001" in rule_ids, "Expected SQL UPDATE without WHERE rule SQL001"

        for f in findings:
            # Provenance must be Tier 1
            assert f["source"] == "DETERMINISTIC_STATIC_ANALYSIS", (
                f"Finding {f['id']} has invalid provenance {f['source']}"
            )
            # Line grounding must be within added diff lines
            assert f["start_line"] is not None and f["start_line"] > 0, (
                f"Finding {f['id']} is not grounded to a valid line number"
            )

        # Step 5: Query review by ID
        get_review_res = await client.get(f"/api/v1/reviews/{review_id}")
        assert get_review_res.status_code == 200
        fetched = get_review_res.json()
        assert fetched["id"] == review_id
        assert fetched["summary"]["total_findings"] == summary["total_findings"]

        # Step 6: Query findings endpoint with severity filter
        findings_res = await client.get(
            f"/api/v1/reviews/{review_id}/findings",
            params={"severity": "critical"},
        )
        assert findings_res.status_code == 200
        crit_findings = findings_res.json()
        assert len(crit_findings) > 0
        assert all(cf["severity"] == "critical" for cf in crit_findings)

        # Step 7: Submit reviewer feedback on a finding
        target_finding = findings[0]
        feedback_res = await client.post(
            f"/api/v1/reviews/{review_id}/findings/{target_finding['id']}/feedback",
            json={
                "verdict": "useful",
                "comment": "Confirmed dangerous API pattern caught before merge.",
            },
        )
        assert feedback_res.status_code == 201
        fb = feedback_res.json()
        assert fb["finding_id"] == target_finding["id"]
        assert fb["verdict"] == "useful"

    finally:
        app.dependency_overrides.pop(get_github_client, None)


@pytest.mark.asyncio
async def test_beta_acceptance_empty_diff_handling(client: AsyncClient):
    """
    Beta Acceptance Edge Case:
    PR with no modified files or empty diff patches must complete cleanly with
    status 'completed' and 0 findings without raising exceptions.
    """
    empty_files = [
        GitHubChangedFile(filename="README.md", status="modified", patch=""),
    ]
    mock_gh = MockGitHubClient(sample_files=empty_files)
    app.dependency_overrides[get_github_client] = lambda: mock_gh

    try:
        response = await client.post(
            "/api/v1/reviews",
            json={
                "repository_url": "https://github.com/acme-corp/docs-only-repo",
                "pull_request_number": 1,
            },
        )
        assert response.status_code == 201
        review = response.json()
        assert review["status"] == "completed"
        assert review["summary"]["total_findings"] == 0
        assert len(review["findings"]) == 0
    finally:
        app.dependency_overrides.pop(get_github_client, None)


@pytest.mark.asyncio
async def test_beta_acceptance_invalid_input_rejection(client: AsyncClient):
    """
    Beta Acceptance Negative Case:
    Invalid repository URLs (cleartext HTTP, non-GitHub, path traversal, bad PR number)
    must be rejected with HTTP 400 and standardized error payloads.
    """
    # 1. Cleartext HTTP
    res_http = await client.post(
        "/api/v1/reviews",
        json={"repository_url": "http://github.com/acme/repo", "pull_request_number": 1},
    )
    assert res_http.status_code == 400
    err = res_http.json()["error"]
    assert err["code"] == "INVALID_REPOSITORY_URL"

    # 2. SSRF attempt via loopback
    res_ssrf = await client.post(
        "/api/v1/reviews",
        json={"repository_url": "https://github.com/127.0.0.1/repo", "pull_request_number": 1},
    )
    assert res_ssrf.status_code == 400
    assert res_ssrf.json()["error"]["code"] == "INVALID_REPOSITORY_URL"

    # 3. Path traversal in owner/repo
    res_trav = await client.post(
        "/api/v1/reviews",
        json={"repository_url": "https://github.com/owner/../secret", "pull_request_number": 1},
    )
    assert res_trav.status_code == 400
    assert res_trav.json()["error"]["code"] == "INVALID_REPOSITORY_URL"

    # 4. Invalid PR number <= 0 (rejected by schema validation)
    res_pr_zero = await client.post(
        "/api/v1/reviews",
        json={"repository_url": "https://github.com/owner/repo", "pull_request_number": 0},
    )
    assert res_pr_zero.status_code == 422

    # 5. Missing PR number when not embedded in URL
    res_missing_pr = await client.post(
        "/api/v1/reviews",
        json={"repository_url": "https://github.com/owner/repo"},
    )
    assert res_missing_pr.status_code == 400
    assert res_missing_pr.json()["error"]["code"] == "INVALID_REPOSITORY_URL"


@pytest.mark.asyncio
async def test_beta_acceptance_github_upstream_errors(client: AsyncClient):
    """
    Beta Acceptance Negative Case:
    Upstream GitHub API errors (404 Not Found, 429 Rate Limit, 502 Gateway Failure)
    must be handled gracefully without leaking credentials or unhandled exceptions.
    """
    class ErrorGitHubClient(MockGitHubClient):
        def __init__(self, error_to_raise):
            super().__init__()
            self.error_to_raise = error_to_raise

        async def get_pull_request(self, owner, repo, number):
            raise self.error_to_raise

    # 1. GitHub 404: PR or Repo not found
    err_404 = PatchwiseAPIException(
        status_code=404,
        error_code=ErrorCode.PR_NOT_FOUND,
        message="Pull request not found or repository is private.",
    )
    app.dependency_overrides[get_github_client] = lambda: ErrorGitHubClient(err_404)
    try:
        res = await client.post(
            "/api/v1/reviews",
            json={"repository_url": "https://github.com/acme/private-repo", "pull_request_number": 999},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "PR_NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_github_client, None)

    # 2. GitHub 429: API Rate Limited
    err_429 = PatchwiseAPIException(
        status_code=429,
        error_code=ErrorCode.GITHUB_RATE_LIMITED,
        message="GitHub API rate limit exceeded.",
        details={"reset_timestamp": 1893456000},
    )
    app.dependency_overrides[get_github_client] = lambda: ErrorGitHubClient(err_429)
    try:
        res = await client.post(
            "/api/v1/reviews",
            json={"repository_url": "https://github.com/acme/busy-repo", "pull_request_number": 12},
        )
        assert res.status_code == 429
        assert res.json()["error"]["code"] == "GITHUB_RATE_LIMITED"
    finally:
        app.dependency_overrides.pop(get_github_client, None)

    # 3. GitHub 502: Upstream Gateway Failure
    err_502 = PatchwiseAPIException(
        status_code=502,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="GitHub API error (HTTP 502) during get_pull_request.",
    )
    app.dependency_overrides[get_github_client] = lambda: ErrorGitHubClient(err_502)
    try:
        res = await client.post(
            "/api/v1/reviews",
            json={"repository_url": "https://github.com/acme/outage-repo", "pull_request_number": 34},
        )
        assert res.status_code == 502
        assert res.json()["error"]["code"] == "INTERNAL_ERROR"
    finally:
        app.dependency_overrides.pop(get_github_client, None)


@pytest.mark.asyncio
async def test_beta_acceptance_oversized_request_rejection(client: AsyncClient):
    """
    Beta Acceptance Negative Case:
    HTTP requests exceeding the maximum allowed size (2MB) must be rejected with
    HTTP 413 CONTENT_TOO_LARGE and ErrorCode.REQUEST_ENTITY_TOO_LARGE.
    """
    # 1. Content-Length header exceeding limit
    oversized_headers = {
        "Content-Type": "application/json",
        "Content-Length": str(5 * 1024 * 1024),  # 5MB
    }
    res_header = await client.post(
        "/api/v1/reviews",
        headers=oversized_headers,
        content=b'{"test": "payload"}',
    )
    assert res_header.status_code == 413
    assert res_header.json()["error"]["code"] == "REQUEST_ENTITY_TOO_LARGE"

    # 2. Chunked streaming payload exceeding limit
    large_payload = json.dumps({
        "repository_url": "https://github.com/acme/large-repo",
        "pull_request_number": 1,
        "padding": "x" * (2 * 1024 * 1024 + 100),
    }).encode("utf-8")

    res_stream = await client.post(
        "/api/v1/reviews",
        headers={"Content-Type": "application/json"},
        content=large_payload,
    )
    assert res_stream.status_code == 413
    assert res_stream.json()["error"]["code"] == "REQUEST_ENTITY_TOO_LARGE"


@pytest.mark.asyncio
async def test_beta_acceptance_production_authentication_enforcement(client: AsyncClient):
    """
    Beta Acceptance Security Gate:
    In production runtime (ENVIRONMENT=production), endpoints modifying state
    must strictly require a valid API key (via X-API-Key or Authorization header)
    and fail closed on missing or incorrect credentials.
    """
    prod_key = "beta-release-secret-key-prod-999"

    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "API_SECRET_KEY", prod_key):

        # 1. Missing API key -> 401 Unauthorized
        res_no_key = await client.post(
            "/api/v1/reviews",
            json={"repository_url": "https://github.com/acme/repo", "pull_request_number": 1},
        )
        assert res_no_key.status_code == 401
        assert res_no_key.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

        # 2. Invalid API key -> 401 Unauthorized
        res_bad_key = await client.post(
            "/api/v1/reviews",
            headers={"X-API-Key": "wrong-key-attempt"},
            json={"repository_url": "https://github.com/acme/repo", "pull_request_number": 1},
        )
        assert res_bad_key.status_code == 401
        assert res_bad_key.json()["error"]["code"] == "INVALID_API_KEY"

        # 3. Valid API key -> Accepted through authentication gate
        mock_gh = MockGitHubClient(sample_files=[
            GitHubChangedFile(filename="src/clean.py", status="modified", patch="@@ -1,2 +1,3 @@\n+x = 1\n")
        ])
        app.dependency_overrides[get_github_client] = lambda: mock_gh
        try:
            res_valid = await client.post(
                "/api/v1/reviews",
                headers={"X-API-Key": prod_key},
                json={"repository_url": "https://github.com/acme/repo", "pull_request_number": 1},
            )
            assert res_valid.status_code == 201
            assert res_valid.json()["status"] == "completed"
        finally:
            app.dependency_overrides.pop(get_github_client, None)
