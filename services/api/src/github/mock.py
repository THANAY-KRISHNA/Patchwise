"""Offline Mock GitHub Client for Unit and Integration Tests."""
from datetime import datetime, timezone
from typing import Dict, List, Optional
from ..core.errors import ErrorCode, PatchwiseAPIException
from .models import GitHubChangedFile, GitHubPullRequest, GitHubRateLimit

# Deterministic sample pull request data
SAMPLE_PYTHON_PATCH = """@@ -10,6 +10,10 @@ def calculate_total(items):
     total = 0
     for item in items:
-        total += item.price
+        # Added validation check
+        if not isinstance(item.price, (int, float)):
+            raise ValueError("Invalid price format")
+        total += item.price
     return total
@@ -30,4 +34,5 @@ def format_receipt(user, total):
     print(f"Receipt for {user.name}")
-    return f"Total: {total}"
+    tax = total * 0.05
+    return f"Total: {total + tax}"
"""

SAMPLE_BINARY_FILE_NAME = "assets/logo.png"


class MockGitHubClient:
    """Mock GitHub Client providing deterministic offline responses for tests."""

    def __init__(
        self,
        simulate_error: Optional[ErrorCode] = None,
        simulate_rate_limit: bool = False,
        sample_files: Optional[List[GitHubChangedFile]] = None,
    ):
        self.simulate_error = simulate_error
        self.simulate_rate_limit = simulate_rate_limit
        self.sample_files = sample_files or [
            GitHubChangedFile(
                filename="src/calculator.py",
                status="modified",
                additions=6,
                deletions=2,
                changes=8,
                patch=SAMPLE_PYTHON_PATCH,
            ),
            GitHubChangedFile(
                filename="docs/architecture.md",
                status="added",
                additions=10,
                deletions=0,
                changes=10,
                patch="@@ -0,0 +1,5 @@\n+# Architecture\n+Details here.",
            ),
            GitHubChangedFile(
                filename="legacy/old_module.py",
                status="removed",
                additions=0,
                deletions=20,
                changes=20,
                patch="@@ -1,5 +0,0 @@\n-def legacy():\n-    pass",
            ),
            GitHubChangedFile(
                filename=SAMPLE_BINARY_FILE_NAME,
                status="added",
                additions=0,
                deletions=0,
                changes=0,
                patch=None,  # Binary files do not have text patches
            ),
        ]

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> GitHubPullRequest:
        if self.simulate_rate_limit:
            raise PatchwiseAPIException(
                status_code=429,
                error_code=ErrorCode.GITHUB_RATE_LIMITED,
                message="GitHub API rate limit exceeded.",
                details={"remaining": 0, "reset_timestamp": 1700000000},
            )

        if self.simulate_error == ErrorCode.PR_NOT_FOUND:
            raise PatchwiseAPIException(
                status_code=404,
                error_code=ErrorCode.PR_NOT_FOUND,
                message="Pull request not found.",
            )
        elif self.simulate_error == ErrorCode.REVIEW_TIMEOUT:
            raise PatchwiseAPIException(
                status_code=504,
                error_code=ErrorCode.REVIEW_TIMEOUT,
                message="GitHub API request timed out.",
            )
        elif self.simulate_error == ErrorCode.INTERNAL_ERROR:
            raise PatchwiseAPIException(
                status_code=401,
                error_code=ErrorCode.INTERNAL_ERROR,
                message="GitHub authentication failed.",
            )

        return GitHubPullRequest(
            number=pr_number,
            title=f"Sample PR #{pr_number} in {owner}/{repo}",
            body="PR description with sample modifications.",
            state="open",
            html_url=f"https://github.com/{owner}/{repo}/pull/{pr_number}",
            base_commit_sha="1111111111111111111111111111111111111111",
            head_commit_sha="2222222222222222222222222222222222222222",
            base_ref="main",
            head_ref="feature-branch",
            author_username="testuser",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            merged_at=None,
            is_draft=False,
        )

    async def get_pull_request_files(
        self, owner: str, repo: str, pr_number: int, per_page: int = 100
    ) -> List[GitHubChangedFile]:
        if self.simulate_rate_limit:
            raise PatchwiseAPIException(
                status_code=429,
                error_code=ErrorCode.GITHUB_RATE_LIMITED,
                message="GitHub API rate limit exceeded.",
            )
        if self.simulate_error:
            await self.get_pull_request(owner, repo, pr_number)

        return self.sample_files

    async def get_rate_limit(self) -> GitHubRateLimit:
        if self.simulate_rate_limit:
            return GitHubRateLimit(limit=60, remaining=0, reset_timestamp=1700000000, used=60)
        return GitHubRateLimit(limit=5000, remaining=4990, reset_timestamp=1700000000, used=10)
