"""End-to-End integration tests for pull request analysis and persistence."""
import pytest
from httpx import AsyncClient
from src.github.client import GitHubClient
from src.github.mock import MockGitHubClient, SAMPLE_PYTHON_PATCH
from src.main import app
from src.routers.reviews import get_github_client


@pytest.mark.asyncio
async def test_end_to_end_pr_review_workflow(client: AsyncClient):
    # Set up mock GitHub client
    mock_gh = MockGitHubClient()
    app.dependency_overrides[get_github_client] = lambda: mock_gh

    try:
        # 1. Submit PR for analysis
        submit_res = await client.post(
            "/api/v1/reviews",
            json={
                "repository_url": "https://github.com/my-org/backend-service",
                "pull_request_number": 99,
            },
        )
        assert submit_res.status_code == 201
        review_data = submit_res.json()
        review_id = review_data["id"]
        assert review_data["status"] == "completed"
        assert review_data["repository"] == "my-org/backend-service"
        assert review_data["pr_number"] == 99
        assert review_data["summary"]["deterministic_count"] > 0

        # 2. Query review by ID
        get_res = await client.get(f"/api/v1/reviews/{review_id}")
        assert get_res.status_code == 200
        fetched_review = get_res.json()
        assert fetched_review["id"] == review_id
        assert fetched_review["summary"]["total_findings"] == review_data["summary"]["total_findings"]

        # 3. Query all findings
        findings_res = await client.get(f"/api/v1/reviews/{review_id}/findings")
        assert findings_res.status_code == 200
        findings = findings_res.json()
        assert len(findings) > 0

        # Check all findings are strictly DETERMINISTIC_STATIC_ANALYSIS
        for f in findings:
            assert f["source"] == "DETERMINISTIC_STATIC_ANALYSIS"
            assert f["file_path"] in ["src/calculator.py", "docs/architecture.md", "legacy/old_module.py"]

        # 4. Filter findings by category
        filtered_res = await client.get(
            f"/api/v1/reviews/{review_id}/findings",
            params={"category": "test_suggestion"},
        )
        assert filtered_res.status_code == 200
        test_findings = filtered_res.json()
        assert all(f["category"] == "test_suggestion" for f in test_findings)

    finally:
        app.dependency_overrides.pop(get_github_client, None)
