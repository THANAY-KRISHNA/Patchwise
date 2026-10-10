"""Review and Pull Request Schemas."""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from .findings import FindingRead


class ReviewStatus(str, Enum):
    QUEUED = "queued"
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ReviewSubmissionRequest(BaseModel):
    repository_url: HttpUrl = Field(
        ...,
        description="Public GitHub repository URL (e.g. https://github.com/owner/repo)",
    )
    pull_request_number: int = Field(..., ge=1, description="GitHub pull request number")


class ReviewSummary(BaseModel):
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    deterministic_count: int = 0
    ai_hypothesis_count: int = 0
    verified_test_count: int = 0
    rule_provider_status: str = "completed"
    ai_provider_status: Optional[str] = None
    ai_provider_name: Optional[str] = None
    ai_error_sanitized: Optional[str] = None


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository: str
    pr_number: int
    pr_title: Optional[str] = None
    commit_sha: Optional[str] = None
    status: ReviewStatus
    engine_version: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_code: Optional[str] = None
    summary: Optional[ReviewSummary] = None
    findings: Optional[List[FindingRead]] = None
