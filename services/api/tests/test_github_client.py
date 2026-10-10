"""Unit tests for GitHub REST API client and offline mock fixture."""
import pytest
import httpx
from src.core.errors import ErrorCode, PatchwiseAPIException
from src.github.client import GitHubClient, parse_github_repo_and_number
from src.github.mock import MockGitHubClient


def test_url_parser_valid_urls():
    owner, repo, pr_num = parse_github_repo_and_number("https://github.com/fastapi/fastapi/pull/42")
    assert owner == "fastapi"
    assert repo == "fastapi"
    assert pr_num == 42

    # Trailing slash
    owner, repo, pr_num = parse_github_repo_and_number("https://github.com/owner-name/repo.js/pull/999/")
    assert owner == "owner-name"
    assert repo == "repo.js"
    assert pr_num == 999

    # owner/repo format with explicit number
    owner, repo, pr_num = parse_github_repo_and_number("my-org/my-repo", pr_number=10)
    assert owner == "my-org"
    assert repo == "my-repo"
    assert pr_num == 10


def test_url_parser_rejects_invalid_inputs():
    invalid_cases = [
        "https://gitlab.com/owner/repo/pull/1",
        "https://evil.attacker.com/github.com/owner/repo/pull/1",
        "ftp://github.com/owner/repo/pull/1",
        "not_a_url",
        "https://github.com/owner/repo",  # Missing PR number
        "https://github.com/owner/repo/issues/1",  # Issue URL, not PR
    ]
    for url in invalid_cases:
        with pytest.raises(PatchwiseAPIException) as exc_info:
            parse_github_repo_and_number(url)
        assert exc_info.value.error_code == ErrorCode.INVALID_REPOSITORY_URL


@pytest.mark.asyncio
async def test_github_client_successful_pr_fetch():
    def handler(request: httpx.Request):
        assert request.url.path == "/repos/owner/repo/pulls/1"
        return httpx.Response(
            200,
            json={
                "number": 1,
                "title": "Fix memory leak",
                "body": "Resolves issue #5",
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/1",
                "base": {"sha": "1111111111111111111111111111111111111111", "ref": "main"},
                "head": {"sha": "2222222222222222222222222222222222222222", "ref": "fix-leak"},
                "user": {"login": "contributor"},
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T01:00:00Z",
            },
            headers={"X-RateLimit-Limit": "5000", "X-RateLimit-Remaining": "4950", "X-RateLimit-Reset": "1700000000"},
        )

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport) as mock_http:
        client = GitHubClient(token="secret-token-123", http_client=mock_http)
        pr = await client.get_pull_request("owner", "repo", 1)
        assert pr.number == 1
        assert pr.title == "Fix memory leak"
        assert pr.base_commit_sha == "1111111111111111111111111111111111111111"
        assert client.rate_limit_info is not None
        assert client.rate_limit_info.remaining == 4950


@pytest.mark.asyncio
async def test_github_client_pagination():
    def handler(request: httpx.Request):
        page = request.url.params.get("page")
        if page == "1":
            return httpx.Response(
                200,
                json=[
                    {"filename": "file1.py", "status": "modified", "additions": 2, "deletions": 1, "changes": 3, "patch": "@@ -1,2 +1,3 @@\n+line"}
                ],
            )
        elif page == "2":
            return httpx.Response(
                200,
                json=[
                    {"filename": "file2.py", "status": "added", "additions": 5, "deletions": 0, "changes": 5, "patch": "@@ -0,0 +1,5 @@\n+line"}
                ],
            )
        else:
            return httpx.Response(200, json=[])

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport) as mock_http:
        # Request with per_page=1 to trigger pagination
        client = GitHubClient(http_client=mock_http)
        files = await client.get_pull_request_files("owner", "repo", 1, per_page=1)
        assert len(files) == 2
        assert files[0].filename == "file1.py"
        assert files[1].filename == "file2.py"


@pytest.mark.asyncio
async def test_github_client_auth_failure_error_mapping():
    def handler(request: httpx.Request):
        return httpx.Response(401, json={"message": "Bad credentials"})

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport) as mock_http:
        client = GitHubClient(token="invalid_token", http_client=mock_http)
        with pytest.raises(PatchwiseAPIException) as exc_info:
            await client.get_pull_request("owner", "repo", 1)
        assert exc_info.value.status_code == 401
        # Token must not appear in exception message
        assert "invalid_token" not in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_github_client_rate_limit_error_mapping():
    def handler(request: httpx.Request):
        return httpx.Response(
            403,
            json={"message": "API rate limit exceeded for user"},
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1700003600"},
        )

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport) as mock_http:
        client = GitHubClient(http_client=mock_http)
        with pytest.raises(PatchwiseAPIException) as exc_info:
            await client.get_pull_request("owner", "repo", 1)
        assert exc_info.value.error_code == ErrorCode.GITHUB_RATE_LIMITED
        assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_github_client_not_found_error_mapping():
    def handler(request: httpx.Request):
        return httpx.Response(404, json={"message": "Not Found"})

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport) as mock_http:
        client = GitHubClient(http_client=mock_http)
        with pytest.raises(PatchwiseAPIException) as exc_info:
            await client.get_pull_request("private-org", "secret-repo", 999)
        assert exc_info.value.error_code == ErrorCode.PR_NOT_FOUND
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_offline_mock_github_client():
    mock_client = MockGitHubClient()
    pr = await mock_client.get_pull_request("facebook", "react", 42)
    assert pr.number == 42
    assert pr.state == "open"
    assert pr.head_commit_sha == "2222222222222222222222222222222222222222"

    files = await mock_client.get_pull_request_files("facebook", "react", 42)
    assert len(files) == 4
    filenames = [f.filename for f in files]
    assert "src/calculator.py" in filenames
    assert "assets/logo.png" in filenames
