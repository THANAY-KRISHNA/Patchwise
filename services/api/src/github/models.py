"""Data Models for GitHub REST API responses."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class GitHubPullRequest(BaseModel):
    """Normalized Pull Request metadata."""
    number: int
    title: str
    body: Optional[str] = None
    state: str
    html_url: str
    base_commit_sha: str
    head_commit_sha: str
    base_ref: str
    head_ref: str
    author_username: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime] = None
    is_draft: bool = False


class GitHubChangedFile(BaseModel):
    """Represents a changed file entry in a pull request."""
    filename: str
    status: str = Field(description="added, modified, removed, renamed, binary")
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: Optional[str] = Field(
        None, description="Unified patch hunk text provided by GitHub API"
    )
    previous_filename: Optional[str] = None
    sha: Optional[str] = None


class GitHubRateLimit(BaseModel):
    """GitHub API Rate Limit information extracted from headers or endpoint."""
    limit: int
    remaining: int
    reset_timestamp: int
    used: int = 0
