"""Schemas and Enums for Findings, Provenance Tiers, and Feedback."""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class FindingProvenance(str, Enum):
    """Three-Tier Provenance Classification mandated by Patchwise architecture."""
    DETERMINISTIC_STATIC_ANALYSIS = "DETERMINISTIC_STATIC_ANALYSIS"
    AI_GENERATED_HYPOTHESIS = "AI_GENERATED_HYPOTHESIS"
    VERIFIED_TEST_RESULT = "VERIFIED_TEST_RESULT"


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    INPUT_VALIDATION = "input_validation"
    EXCEPTION_HANDLING = "exception_handling"
    BOUNDARY_CONDITION = "boundary_condition"
    RESOURCE_CLEANUP = "resource_cleanup"
    SECURITY_PATTERN = "security_pattern"
    TEST_SUGGESTION = "test_suggestion"
    CODE_QUALITY = "code_quality"


class FeedbackVerdict(str, Enum):
    USEFUL = "useful"
    INCORRECT = "incorrect"
    IRRELEVANT = "irrelevant"


class FindingBase(BaseModel):
    rule_id: str = Field(..., description="Stable rule identifier, e.g., 'PY001'")
    source: FindingProvenance = Field(
        ...,
        description="Provenance tier: DETERMINISTIC_STATIC_ANALYSIS, AI_GENERATED_HYPOTHESIS, or VERIFIED_TEST_RESULT",
    )
    severity: FindingSeverity
    category: FindingCategory
    file_path: str
    start_line: Optional[int] = Field(None, ge=1, description="1-indexed line number in changed file")
    end_line: Optional[int] = Field(None, ge=1, description="1-indexed line number in changed file")
    title: str = Field(..., min_length=3, max_length=255)
    explanation: str = Field(..., min_length=5)
    suggested_fix: Optional[str] = None
    fingerprint: Optional[str] = Field(None, description="SHA-256 fingerprint for deduplication")


class FindingCreate(FindingBase):
    pass


class FindingRead(FindingBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_id: UUID
    created_at: datetime


class FeedbackBase(BaseModel):
    verdict: FeedbackVerdict
    comment: Optional[str] = None


class FeedbackCreate(FeedbackBase):
    pass


class FeedbackRead(FeedbackBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    finding_id: UUID
    created_at: datetime
