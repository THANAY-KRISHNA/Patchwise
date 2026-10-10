"""Unit tests for typed schemas and provenance separation."""
import pytest
from pydantic import ValidationError
from src.schemas.findings import (
    FeedbackBase,
    FeedbackVerdict,
    FindingBase,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
)
from src.schemas.reviews import ReviewStatus, ReviewSubmissionRequest


def test_finding_provenance_tiers():
    """Verify that all three mandated provenance tiers are recognized."""
    tiers = [
        FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        FindingProvenance.AI_GENERATED_HYPOTHESIS,
        FindingProvenance.VERIFIED_TEST_RESULT,
    ]
    assert len(tiers) == 3
    assert FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS.value == "DETERMINISTIC_STATIC_ANALYSIS"
    assert FindingProvenance.AI_GENERATED_HYPOTHESIS.value == "AI_GENERATED_HYPOTHESIS"
    assert FindingProvenance.VERIFIED_TEST_RESULT.value == "VERIFIED_TEST_RESULT"


def test_valid_finding_creation():
    finding = FindingBase(
        rule_id="PY001",
        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        severity=FindingSeverity.HIGH,
        category=FindingCategory.INPUT_VALIDATION,
        file_path="src/main.py",
        start_line=42,
        end_line=45,
        title="Unvalidated user payload",
        explanation="Payload field accessed before verification.",
        suggested_fix="Validate against schema.",
    )
    assert finding.rule_id == "PY001"
    assert finding.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert finding.start_line == 42


def test_invalid_finding_line_number():
    with pytest.raises(ValidationError):
        FindingBase(
            rule_id="PY001",
            source=FindingProvenance.AI_GENERATED_HYPOTHESIS,
            severity=FindingSeverity.MEDIUM,
            category=FindingCategory.BOUNDARY_CONDITION,
            file_path="src/main.py",
            start_line=0,  # Line number must be >= 1
            title="Boundary check",
            explanation="Array index out of bounds.",
        )


def test_review_status_enums():
    assert ReviewStatus.QUEUED.value == "queued"
    assert ReviewStatus.ANALYZING.value == "analyzing"
    assert ReviewStatus.COMPLETED.value == "completed"
    assert ReviewStatus.FAILED.value == "failed"


def test_review_submission_request():
    req = ReviewSubmissionRequest(
        repository_url="https://github.com/facebook/react",
        pull_request_number=123,
    )
    assert str(req.repository_url).rstrip("/") == "https://github.com/facebook/react"
    assert req.pull_request_number == 123


def test_feedback_verdicts():
    fb = FeedbackBase(verdict=FeedbackVerdict.USEFUL, comment="Caught an edge case")
    assert fb.verdict == FeedbackVerdict.USEFUL
    assert fb.comment == "Caught an edge case"
