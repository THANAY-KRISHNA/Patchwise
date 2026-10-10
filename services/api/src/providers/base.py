"""Abstract Review Provider Interface and Execution Contexts."""
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field

from ..analyzer.base import CandidateFinding
from ..github.models import GitHubPullRequest
from ..parser.models import ParsedDiffResult
from ..schemas.findings import FindingBase


class ReviewContext(BaseModel):
    """Contextual metadata and parsed diff provided to review providers."""
    repository: str
    pr_number: int
    pr_metadata: GitHubPullRequest
    parsed_diff: ParsedDiffResult
    engine_version: str = "0.1.0"


class ReviewResult(BaseModel):
    """Aggregated output produced by a review provider."""
    provider_name: str
    findings: List[CandidateFinding] = Field(default_factory=list)
    raw_findings_count: int = 0
    grounded_findings_count: int = 0
    duration_ms: int = 0
    status: str = "completed"
    error_message: Optional[str] = None


class BaseReviewProvider(ABC):
    """Abstract interface that all review engines (Rule-Only or LLM-assisted) implement."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'rule_only', 'openai', 'gemini')."""
        pass

    @abstractmethod
    async def review(self, context: ReviewContext) -> ReviewResult:
        """Execute review against the given context."""
        pass
