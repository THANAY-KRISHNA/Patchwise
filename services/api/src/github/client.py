import ipaddress
import logging
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse
import httpx
from ..core.config import settings
from ..core.errors import ErrorCode, PatchwiseAPIException
from .models import GitHubChangedFile, GitHubPullRequest, GitHubRateLimit

logger = logging.getLogger("patchwise.github")

# Strict URL pattern allowlisting only secure public HTTPS github.com PR URLs
GITHUB_PR_URL_REGEX = re.compile(
    r"^https://github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)/pull/(\d+)/?$"
)

GITHUB_REPO_URL_REGEX = re.compile(
    r"^https://github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)/?$"
)


def _validate_owner_repo(owner: str, repo: str) -> None:
    """Validate that repository owner and name do not contain directory traversal or dot sequences."""
    if owner in (".", "..") or repo in (".", "..") or ".." in owner or ".." in repo:
        raise PatchwiseAPIException(
            status_code=400,
            error_code=ErrorCode.INVALID_REPOSITORY_URL,
            message=f"Invalid repository specification '{owner}/{repo}' containing illegal path traversal sequences.",
        )
    if owner.startswith(("-", ".")) or owner.endswith(("-", ".")) or repo.startswith("."):
        raise PatchwiseAPIException(
            status_code=400,
            error_code=ErrorCode.INVALID_REPOSITORY_URL,
            message=f"Invalid repository specification '{owner}/{repo}'.",
        )

    # Disallow localhost and raw IP addresses as owner or repository to prevent SSRF confusion
    for part in (owner, repo):
        if part.lower() == "localhost":
            raise PatchwiseAPIException(
                status_code=400,
                error_code=ErrorCode.INVALID_REPOSITORY_URL,
                message=f"Invalid repository specification '{owner}/{repo}': localhost is prohibited.",
            )
        try:
            ipaddress.ip_address(part)
            raise PatchwiseAPIException(
                status_code=400,
                error_code=ErrorCode.INVALID_REPOSITORY_URL,
                message=f"Invalid repository specification '{owner}/{repo}': IP addresses are prohibited.",
            )
        except ValueError:
            pass


def parse_github_repo_and_number(
    url_or_repo: str, pr_number: Optional[int] = None
) -> Tuple[str, str, int]:
    """
    Safely parse and normalize GitHub owner, repo, and PR number.
    Accepts full HTTPS PR URL, HTTPS repo URL with separate pr_number, or 'owner/repo' with pr_number.
    Rejects malformed input, internal IPs, insecure HTTP, and non-GitHub hosts cleanly.
    """
    clean_input = url_or_repo.strip()

    # Reject user credentials in URLs (e.g. https://user:pass@github.com)
    if "@" in clean_input:
        raise PatchwiseAPIException(
            status_code=400,
            error_code=ErrorCode.INVALID_REPOSITORY_URL,
            message="Embedded user credentials in repository URLs are prohibited.",
        )

    # Reject query parameters and fragments
    if "?" in clean_input or "#" in clean_input:
        raise PatchwiseAPIException(
            status_code=400,
            error_code=ErrorCode.INVALID_REPOSITORY_URL,
            message="Repository URLs must not contain query parameters or fragments.",
        )

    # Reject encoded path traversal sequences or backslashes
    lower_input = clean_input.lower()
    if "%2e" in lower_input or "%2f" in lower_input or "%5c" in lower_input or "\\" in clean_input:
        raise PatchwiseAPIException(
            status_code=400,
            error_code=ErrorCode.INVALID_REPOSITORY_URL,
            message="Illegal URL-encoded characters or backslashes detected.",
        )

    # Reject cleartext HTTP for secure transmission
    if clean_input.lower().startswith("http://"):
        raise PatchwiseAPIException(
            status_code=400,
            error_code=ErrorCode.INVALID_REPOSITORY_URL,
            message=f"Insecure HTTP repository URL '{clean_input}' is prohibited. Only secure HTTPS URLs (https://github.com/...) are supported.",
        )

    # Reject any non-GitHub URL scheme
    if "://" in clean_input and not clean_input.startswith("https://github.com/"):
        raise PatchwiseAPIException(
            status_code=400,
            error_code=ErrorCode.INVALID_REPOSITORY_URL,
            message=f"Unsupported repository host or scheme in '{clean_input}'. Only 'https://github.com/...' is supported.",
        )

    # Check full PR URL (https://github.com/owner/repo/pull/123)
    match_pr = GITHUB_PR_URL_REGEX.match(clean_input)
    if match_pr:
        owner, repo, number_str = match_pr.groups()
        _validate_owner_repo(owner, repo)
        pr_num = int(number_str)
        if pr_num < 1:
            raise PatchwiseAPIException(
                status_code=400,
                error_code=ErrorCode.INVALID_REPOSITORY_URL,
                message=f"Invalid pull request number: {pr_num}. Must be >= 1.",
            )
        return owner, repo, pr_num

    # Check repository URL with separate pr_number (https://github.com/owner/repo)
    if pr_number is not None and pr_number >= 1:
        match_repo = GITHUB_REPO_URL_REGEX.match(clean_input)
        if match_repo:
            owner, repo = match_repo.groups()
            _validate_owner_repo(owner, repo)
            return owner, repo, pr_number

        # Check owner/repo format (e.g. 'owner/repo')
        parts = clean_input.split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            if re.match(r"^[a-zA-Z0-9_\-\.]+$", parts[0]) and re.match(r"^[a-zA-Z0-9_\-\.]+$", parts[1]):
                _validate_owner_repo(parts[0], parts[1])
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
        clean_base = base_url.rstrip("/")
        parsed_base = urlparse(clean_base)
        if parsed_base.scheme != "https":
            raise PatchwiseAPIException(
                status_code=400,
                error_code=ErrorCode.INVALID_REPOSITORY_URL,
                message=f"Insecure GitHub API base URL '{base_url}'. Only HTTPS is permitted.",
            )
        base_host = (parsed_base.hostname or "").lower()
        if base_host in ("localhost", "127.0.0.1", "::1", "169.254.169.254") or base_host.startswith("127."):
            raise PatchwiseAPIException(
                status_code=400,
                error_code=ErrorCode.INVALID_REPOSITORY_URL,
                message=f"Illegal GitHub API host '{base_host}': Loopback and link-local metadata addresses are prohibited.",
            )

        self.base_url = clean_base
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
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
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
            from ..core.errors import sanitize_secret_text
            logger.error("GitHub request failed: %s", sanitize_secret_text(str(exc)))
            raise PatchwiseAPIException(
                status_code=502,
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to establish connection to GitHub API.",
            )

        # Validate redirects to prevent SSRF and token leakage to third parties
        if response.is_redirect:
            redirect_target = response.headers.get("location", "")
            parsed_loc = urlparse(redirect_target)
            if parsed_loc.scheme != "https" or (parsed_loc.hostname or "").lower() != "api.github.com":
                raise PatchwiseAPIException(
                    status_code=502,
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message="Refusing redirect from GitHub API to an untrusted external host or non-HTTPS location.",
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
