"""Modular Async GitHub REST API Client."""
import logging
import re
from typing import List, Optional, Tuple
import httpx
from ..core.config import settings
from ..core.errors import ErrorCode, PatchwiseAPIException
from .models import GitHubChangedFile, GitHubPullRequest, GitHubRateLimit

logger = logging.getLogger("patchwise.github")

# Strict URL pattern allowlisting only public github.com PR URLs
GITHUB_PR_URL_REGEX = re.compile(
    r"^https?://github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)/pull/(\d+)/?$"
)


GITHUB_REPO_URL_REGEX = re.compile(
    r"^https?://github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)/?$"
)


def parse_github_repo_and_number(
    url_or_repo: str, pr_number: Optional[int] = None
) -> Tuple[str, str, int]:
    """
    Safely parse and normalize GitHub owner, repo, and PR number.
    Accepts full PR URL, repo URL with separate pr_number, or 'owner/repo' with pr_number.
    Rejects malformed input, internal IPs, and non-GitHub hosts cleanly.
    """
    clean_input = url_or_repo.strip()

    # Check full PR URL (https://github.com/owner/repo/pull/123)
    match_pr = GITHUB_PR_URL_REGEX.match(clean_input)
    if match_pr:
        owner, repo, number_str = match_pr.groups()
        return owner, repo, int(number_str)

    # Check repository URL with separate pr_number (https://github.com/owner/repo)
    if pr_number is not None and pr_number >= 1:
        match_repo = GITHUB_REPO_URL_REGEX.match(clean_input)
        if match_repo:
            owner, repo = match_repo.groups()
            return owner, repo, pr_number

        # Check owner/repo format (e.g. 'owner/repo')
        parts = clean_input.split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            if re.match(r"^[a-zA-Z0-9_\-\.]+$", parts[0]) and re.match(r"^[a-zA-Z0-9_\-\.]+$", parts[1]):
                return parts[0], parts[1], pr_number

    raise PatchwiseAPIException(
        status_code=400,
        error_code=ErrorCode.INVALID_REPOSITORY_URL,
        message=f"Invalid GitHub PR URL or repository specification: '{clean_input}'. Expected format: https://github.com/owner/repo/pull/123 or repository URL with PR number.",
    )


class GitHubClient:
    """
    Async client for GitHub REST API v3.
    Supports injectable HTTP client for unit tests and offline mock fixtures.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://api.github.com",
        http_client: Optional[httpx.AsyncClient] = None,
        timeout: float = 15.0,
    ):
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = base_url.rstrip("/")
        self._custom_client = http_client
        self.timeout = timeout
        self.rate_limit_info: Optional[GitHubRateLimit] = None

    def _get_headers(self) -> dict:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Patchwise-PR-Assistant/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _update_rate_limits(self, headers: httpx.Headers):
        try:
            limit = int(headers.get("X-RateLimit-Limit", 0))
            remaining = int(headers.get("X-RateLimit-Remaining", 0))
            reset = int(headers.get("X-RateLimit-Reset", 0))
            used = int(headers.get("X-RateLimit-Used", 0))
            if limit > 0:
                self.rate_limit_info = GitHubRateLimit(
                    limit=limit,
                    remaining=remaining,
                    reset_timestamp=reset,
                    used=used,
                )
        except Exception:
            pass

    def _handle_error_response(self, response: httpx.Response, context: str):
        self._update_rate_limits(response.headers)
        status_code = response.status_code

        # 401 Unauthorized
        if status_code == 401:
            raise PatchwiseAPIException(
                status_code=401,
                error_code=ErrorCode.INTERNAL_ERROR,
                message="GitHub authentication failed. Please check configured credentials.",
            )

        # 403 Forbidden / 429 Rate Limit
        if status_code in (403, 429):
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            resp_text = response.text.lower()
            if remaining == "0" or "rate limit" in resp_text or "secondary rate limit" in resp_text:
                raise PatchwiseAPIException(
                    status_code=429,
                    error_code=ErrorCode.GITHUB_RATE_LIMITED,
                    message="GitHub API rate limit exceeded.",
                    details={"reset_timestamp": reset, "remaining": remaining},
                )
            raise PatchwiseAPIException(
                status_code=403,
                error_code=ErrorCode.PR_NOT_FOUND,
                message="Access to the repository or pull request is forbidden. It may be private or restricted.",
            )

        # 404 Not Found
        if status_code == 404:
            raise PatchwiseAPIException(
                status_code=404,
                error_code=ErrorCode.PR_NOT_FOUND,
                message=f"Pull request not found or repository is private/inaccessible ({context}).",
            )

        # General error
        raise PatchwiseAPIException(
            status_code=502,
            error_code=ErrorCode.INTERNAL_ERROR,
            message=f"GitHub API error (HTTP {status_code}) during {context}.",
        )

    async def _request(self, method: str, path: str, params: Optional[dict] = None) -> httpx.Response:
        url = f"{self.base_url}{path}"
        headers = self._get_headers()

        try:
            if self._custom_client:
                response = await self._custom_client.request(
                    method=method, url=url, headers=headers, params=params, timeout=self.timeout
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method, url=url, headers=headers, params=params
                    )
        except httpx.TimeoutException:
            raise PatchwiseAPIException(
                status_code=504,
                error_code=ErrorCode.REVIEW_TIMEOUT,
                message="GitHub API request timed out.",
            )
        except httpx.RequestError as exc:
            logger.error("GitHub request failed: %s", str(exc))
            raise PatchwiseAPIException(
                status_code=502,
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to establish connection to GitHub API.",
            )

        if not response.is_success:
            self._handle_error_response(response, context=f"{method} {path}")

        self._update_rate_limits(response.headers)
        return response

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> GitHubPullRequest:
        """Fetch pull request metadata from GitHub."""
        path = f"/repos/{owner}/{repo}/pulls/{pr_number}"
        response = await self._request("GET", path)
        data = response.json()

        return GitHubPullRequest(
            number=data["number"],
            title=data.get("title", ""),
            body=data.get("body"),
            state=data.get("state", "open"),
            html_url=data.get("html_url", f"https://github.com/{owner}/{repo}/pull/{pr_number}"),
            base_commit_sha=data["base"]["sha"],
            head_commit_sha=data["head"]["sha"],
            base_ref=data["base"]["ref"],
            head_ref=data["head"]["ref"],
            author_username=data.get("user", {}).get("login"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            merged_at=data.get("merged_at"),
            is_draft=data.get("draft", False),
        )

    async def get_pull_request_files(
        self, owner: str, repo: str, pr_number: int, per_page: int = 100
    ) -> List[GitHubChangedFile]:
        """
        Fetch all changed file patches for a pull request, supporting pagination.
        """
        changed_files: List[GitHubChangedFile] = []
        page = 1

        while True:
            path = f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
            response = await self._request("GET", path, params={"per_page": per_page, "page": page})
            data = response.json()

            if not data or not isinstance(data, list):
                break

            for item in data:
                changed_files.append(
                    GitHubChangedFile(
                        filename=item["filename"],
                        status=item.get("status", "modified"),
                        additions=item.get("additions", 0),
                        deletions=item.get("deletions", 0),
                        changes=item.get("changes", 0),
                        patch=item.get("patch"),
                        previous_filename=item.get("previous_filename"),
                        sha=item.get("sha"),
                    )
                )

            # GitHub returns fewer items than per_page on the final page
            if len(data) < per_page:
                break
            page += 1

        return changed_files

    async def get_rate_limit(self) -> GitHubRateLimit:
        """Fetch active rate limit status."""
        response = await self._request("GET", "/rate_limit")
        data = response.json()
        core = data.get("resources", {}).get("core", {})
        return GitHubRateLimit(
            limit=core.get("limit", 60),
            remaining=core.get("remaining", 60),
            reset_timestamp=core.get("reset", 0),
            used=core.get("used", 0),
        )
