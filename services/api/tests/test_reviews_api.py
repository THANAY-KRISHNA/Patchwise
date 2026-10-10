"""Integration tests for the reviews/diff inspection API endpoint."""
import pytest
from httpx import AsyncClient
from src.github.mock import MockGitHubClient
from src.main import app
from src.routers.reviews import get_github_client


@pytest.mark.asyncio
async def test_inspect_diff_endpoint_with_mock_github(client: AsyncClient):
    # Override GitHubClient dependency with MockGitHubClient for offline testing
    mock_gh = MockGitHubClient()
    app.dependency_overrides[get_github_client] = lambda: mock_gh

    try:
        response = await client.post(
            "/api/v1/reviews/inspect",
            json={
                "repository_url": "https://github.com/facebook/react",
                "pull_request_number": 1234,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["repository"] == "facebook/react"
        assert data["pr_number"] == 1234
        assert data["total_files_changed"] == 4
        assert data["total_added_lines"] > 0
        assert len(data["files"]) == 4

        # Verify calculator.py file has hunks with added lines
        calc_file = next(f for f in data["files"] if f["file_path"] == "src/calculator.py")
        assert len(calc_file["added_lines"]) > 0
    finally:
        app.dependency_overrides.pop(get_github_client, None)


@pytest.mark.asyncio
async def test_inspect_diff_endpoint_invalid_url(client: AsyncClient):
    response = await client.post(
        "/api/v1/reviews/inspect",
        json={
            "repository_url": "https://gitlab.com/facebook/react",
            "pull_request_number": 1234,
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_REPOSITORY_URL"
