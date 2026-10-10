"""Unit tests for Line Grounding Validator."""
import pytest
from src.parser.diff_parser import parse_unified_diff
from src.schemas.findings import FindingBase, FindingCategory, FindingProvenance, FindingSeverity
from src.validator.grounding import LineGroundingValidator, ValidationRejectionReason

SAMPLE_DIFF = """diff --git a/src/service.py b/src/service.py
index 1234567..89abcdef 100644
--- a/src/service.py
+++ b/src/service.py
@@ -10,5 +10,8 @@ def process(request):
     # Context line 10
     data = request.json()
-    old_call(data)
+    # Added line 12
+    if not data:
+        raise ValueError("Missing data")
+    new_call(data)
     return data
diff --git a/assets/banner.png b/assets/banner.png
Binary files a/assets/banner.png and b/assets/banner.png differ
diff --git a/legacy/old.py b/legacy/old.py
deleted file mode 100644
--- a/legacy/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def dead_code():
-    pass
"""


@pytest.fixture
def validator():
    parsed = parse_unified_diff(SAMPLE_DIFF)
    return LineGroundingValidator(parsed)


def test_valid_finding_on_added_line(validator: LineGroundingValidator):
    finding = FindingBase(
        rule_id="PY001",
        source=FindingProvenance.AI_GENERATED_HYPOTHESIS,
        severity=FindingSeverity.HIGH,
        category=FindingCategory.INPUT_VALIDATION,
        file_path="src/service.py",
        start_line=13,
        end_line=13,
        title="Input check",
        explanation="Validated data payload.",
    )
    result = validator.validate_finding(finding)
    assert result.is_valid is True
    assert result.rejection_reason is None
    assert 13 in result.anchored_changed_lines
    assert result.provenance == FindingProvenance.AI_GENERATED_HYPOTHESIS


def test_valid_finding_across_multi_line_range(validator: LineGroundingValidator):
    finding = FindingBase(
        rule_id="PY002",
        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        severity=FindingSeverity.MEDIUM,
        category=FindingCategory.EXCEPTION_HANDLING,
        file_path="src/service.py",
        start_line=12,
        end_line=15,
        title="Check validation block",
        explanation="Exception path.",
    )
    result = validator.validate_finding(finding)
    assert result.is_valid is True
    # Lines 12, 13, 14, 15 are all added lines
    assert set([12, 13, 14, 15]).issubset(set(result.anchored_changed_lines))


def test_reject_out_of_hunk_line(validator: LineGroundingValidator):
    finding = FindingBase(
        rule_id="PY001",
        source=FindingProvenance.AI_GENERATED_HYPOTHESIS,
        severity=FindingSeverity.LOW,
        category=FindingCategory.CODE_QUALITY,
        file_path="src/service.py",
        start_line=100,  # Line 100 does not exist in any hunk
        end_line=100,
        title="Fabricated line hallucination",
        explanation="Pointing to unchanged distant line.",
    )
    result = validator.validate_finding(finding)
    assert result.is_valid is False
    assert result.rejection_reason == ValidationRejectionReason.OUT_OF_HUNK_RANGE


def test_reject_unmodified_context_line(validator: LineGroundingValidator):
    # Line 10 in new file is context: "# Context line 10"
    finding = FindingBase(
        rule_id="PY001",
        source=FindingProvenance.AI_GENERATED_HYPOTHESIS,
        severity=FindingSeverity.LOW,
        category=FindingCategory.CODE_QUALITY,
        file_path="src/service.py",
        start_line=10,
        end_line=10,
        title="Context-only finding",
        explanation="Pointing to unchanged line 10.",
    )
    result = validator.validate_finding(finding, require_changed_line=True)
    assert result.is_valid is False
    assert result.rejection_reason == ValidationRejectionReason.TARGETS_UNMODIFIED_CONTEXT


def test_reject_file_not_in_diff(validator: LineGroundingValidator):
    finding = FindingBase(
        rule_id="PY001",
        source=FindingProvenance.VERIFIED_TEST_RESULT,
        severity=FindingSeverity.HIGH,
        category=FindingCategory.TEST_SUGGESTION,
        file_path="nonexistent/other.py",
        start_line=1,
        end_line=1,
        title="Nonexistent file",
        explanation="File not touched in PR.",
    )
    result = validator.validate_finding(finding)
    assert result.is_valid is False
    assert result.rejection_reason == ValidationRejectionReason.FILE_NOT_IN_DIFF


def test_reject_binary_file_line_finding(validator: LineGroundingValidator):
    finding = FindingBase(
        rule_id="SEC01",
        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        severity=FindingSeverity.CRITICAL,
        category=FindingCategory.SECURITY_PATTERN,
        file_path="assets/banner.png",
        start_line=5,
        end_line=5,
        title="Binary file finding",
        explanation="Cannot anchor line numbers in binary files.",
    )
    result = validator.validate_finding(finding)
    assert result.is_valid is False
    assert result.rejection_reason == ValidationRejectionReason.FILE_IS_BINARY


def test_reject_deleted_file_line_finding(validator: LineGroundingValidator):
    finding = FindingBase(
        rule_id="PY001",
        source=FindingProvenance.AI_GENERATED_HYPOTHESIS,
        severity=FindingSeverity.LOW,
        category=FindingCategory.CODE_QUALITY,
        file_path="legacy/old.py",
        start_line=1,
        end_line=1,
        title="Deleted file finding",
        explanation="Cannot anchor to deleted file.",
    )
    result = validator.validate_finding(finding)
    assert result.is_valid is False
    assert result.rejection_reason == ValidationRejectionReason.FILE_IS_DELETED


def test_reject_inverted_line_range(validator: LineGroundingValidator):
    finding = FindingBase(
        rule_id="PY001",
        source=FindingProvenance.AI_GENERATED_HYPOTHESIS,
        severity=FindingSeverity.LOW,
        category=FindingCategory.CODE_QUALITY,
        file_path="src/service.py",
        start_line=20,
        end_line=10,  # Invalid: start > end
        title="Inverted lines",
        explanation="Start greater than end.",
    )
    result = validator.validate_finding(finding)
    assert result.is_valid is False
    assert result.rejection_reason == ValidationRejectionReason.INVALID_LINE_RANGE


def test_file_level_findings_policy(validator: LineGroundingValidator):
    finding = FindingBase(
        rule_id="TEST01",
        source=FindingProvenance.VERIFIED_TEST_RESULT,
        severity=FindingSeverity.MEDIUM,
        category=FindingCategory.TEST_SUGGESTION,
        file_path="src/service.py",
        start_line=None,
        end_line=None,
        title="Missing tests for service",
        explanation="File-level recommendation.",
    )
    # When file-level is allowed
    res_allowed = validator.validate_finding(finding, allow_file_level=True)
    assert res_allowed.is_valid is True
    assert res_allowed.is_file_level is True

    # When file-level is disallowed
    res_disallowed = validator.validate_finding(finding, allow_file_level=False)
    assert res_disallowed.is_valid is False
    assert res_disallowed.rejection_reason == ValidationRejectionReason.MISSING_LINE_ANCHOR


def test_filter_and_validate_batch(validator: LineGroundingValidator):
    valid_finding = FindingBase(
        rule_id="PY001",
        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        severity=FindingSeverity.HIGH,
        category=FindingCategory.INPUT_VALIDATION,
        file_path="src/service.py",
        start_line=13,
        end_line=13,
        title="Valid finding",
        explanation="Valid added line.",
    )
    invalid_finding = FindingBase(
        rule_id="PY002",
        source=FindingProvenance.AI_GENERATED_HYPOTHESIS,
        severity=FindingSeverity.LOW,
        category=FindingCategory.CODE_QUALITY,
        file_path="src/service.py",
        start_line=999,
        end_line=999,
        title="Invalid finding",
        explanation="Ungrounded hallucination.",
    )
    accepted, reports = validator.filter_and_validate_findings(
        [valid_finding, invalid_finding], require_changed_line=True
    )
    assert len(accepted) == 1
    assert accepted[0].rule_id == "PY001"
    assert len(reports) == 2
    assert reports[0].is_valid is True
    assert reports[1].is_valid is False
    assert reports[1].rejection_reason == ValidationRejectionReason.OUT_OF_HUNK_RANGE
