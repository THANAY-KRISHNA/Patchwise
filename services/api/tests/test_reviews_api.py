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


@pytest.mark.asyncio
async def test_list_recent_reviews_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/reviews?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_latest_benchmark_summary_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/benchmarks/latest")
    assert response.status_code == 200
    data = response.json()
    assert "dataset_name" in data or "status" in data


@pytest.mark.asyncio
async def test_submit_finding_feedback_flow(client: AsyncClient):
    # 1. Create a review first with mock github
    mock_gh = MockGitHubClient()
    app.dependency_overrides[get_github_client] = lambda: mock_gh
    try:
        rev_res = await client.post(
            "/api/v1/reviews",
            json={
                "repository_url": "https://github.com/facebook/react",
                "pull_request_number": 1234,
            },
        )
        assert rev_res.status_code == 201
        review = rev_res.json()
        review_id = review["id"]
        findings = review["findings"]
        assert len(findings) > 0
        finding_id = findings[0]["id"]

        # 2. Submit feedback
        fb_res = await client.post(
            f"/api/v1/reviews/{review_id}/findings/{finding_id}/feedback",
            json={
                "verdict": "useful",
                "comment": "Accurate detection of unchecked payload access.",
            },
        )
        assert fb_res.status_code == 201
        fb_data = fb_res.json()
        assert fb_data["verdict"] == "useful"
        assert fb_data["finding_id"] == finding_id
        assert fb_data["comment"] == "Accurate detection of unchecked payload access."
    finally:
        app.dependency_overrides.pop(get_github_client, None)

