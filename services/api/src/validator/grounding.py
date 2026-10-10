"""Line Grounding Validator for Pull Request Findings."""
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from ..analyzer.base import CandidateFinding
from ..parser.models import FileChangeStatus, ParsedDiffResult, ParsedFileDiff
from ..schemas.findings import FindingBase, FindingProvenance


class ValidationRejectionReason(str, Enum):
    FILE_NOT_IN_DIFF = "FILE_NOT_IN_DIFF"
    FILE_IS_BINARY = "FILE_IS_BINARY"
    FILE_IS_DELETED = "FILE_IS_DELETED"
    INVALID_LINE_RANGE = "INVALID_LINE_RANGE"
    LINE_OUT_OF_BOUNDS = "LINE_OUT_OF_BOUNDS"
    TARGETS_DELETED_LINE = "TARGETS_DELETED_LINE"
    TARGETS_UNMODIFIED_CONTEXT = "TARGETS_UNMODIFIED_CONTEXT"
    OUT_OF_HUNK_RANGE = "OUT_OF_HUNK_RANGE"
    MISSING_LINE_ANCHOR = "MISSING_LINE_ANCHOR"


class GroundingValidationResult(BaseModel):
    """Structured validation outcome for a single finding."""
    is_valid: bool
    rejection_reason: Optional[ValidationRejectionReason] = None
    details: Optional[str] = None
    file_path: str
    requested_start_line: Optional[int] = None
    requested_end_line: Optional[int] = None
    is_file_level: bool = False
    provenance: FindingProvenance
    anchored_changed_lines: List[int] = Field(default_factory=list)


def _normalize_path(path: str) -> str:
    """Normalize file path for consistent matching across Git diffs and repos."""
    clean = path.strip().replace("\\", "/")
    if clean.startswith("a/") or clean.startswith("b/"):
        clean = clean[2:]
    return clean.lstrip("/")


class LineGroundingValidator:
    """
    Validates that findings reference actual changed lines in the pull request.
    Strictly prevents LLM line hallucinations from being shown as valid code-level defects.
    """

    def __init__(self, parsed_diff: ParsedDiffResult):
        self.parsed_diff = parsed_diff
        self._files_map: Dict[str, ParsedFileDiff] = {}
        for f in parsed_diff.files:
            norm_path = _normalize_path(f.file_path)
            self._files_map[norm_path] = f
            if f.old_path:
                self._files_map[_normalize_path(f.old_path)] = f
            if f.new_path:
                self._files_map[_normalize_path(f.new_path)] = f

    def validate_finding(
        self,
        finding: Union[FindingBase, CandidateFinding],
        require_changed_line: bool = True,
        allow_file_level: bool = False,
    ) -> GroundingValidationResult:
        """
        Validate a single finding against the diff line mapping.
        Never silently mutates invalid lines into valid ones.
        """
        norm_path = _normalize_path(finding.file_path)
        provenance = finding.source

        # 1. Verify file exists in diff
        if norm_path not in self._files_map:
            return GroundingValidationResult(
                is_valid=False,
                rejection_reason=ValidationRejectionReason.FILE_NOT_IN_DIFF,
                details=f"File '{finding.file_path}' is not present in the changed files of this pull request.",
                file_path=finding.file_path,
                requested_start_line=finding.start_line,
                requested_end_line=finding.end_line,
                is_file_level=False,
                provenance=provenance,
            )

        file_diff = self._files_map[norm_path]

        # 2. Check binary files
        if file_diff.is_binary:
            if finding.start_line is not None or finding.end_line is not None:
                return GroundingValidationResult(
                    is_valid=False,
                    rejection_reason=ValidationRejectionReason.FILE_IS_BINARY,
                    details=f"File '{finding.file_path}' is a binary file; line-level findings cannot be anchored.",
                    file_path=finding.file_path,
                    requested_start_line=finding.start_line,
                    requested_end_line=finding.end_line,
                    is_file_level=False,
                    provenance=provenance,
                )
            if allow_file_level:
                return GroundingValidationResult(
                    is_valid=True,
                    file_path=finding.file_path,
                    is_file_level=True,
                    provenance=provenance,
                )
            return GroundingValidationResult(
                is_valid=False,
                rejection_reason=ValidationRejectionReason.MISSING_LINE_ANCHOR,
                details=f"File '{finding.file_path}' is binary and file-level findings are disabled.",
                file_path=finding.file_path,
                provenance=provenance,
            )

        # 3. Check deleted files
        if file_diff.status == FileChangeStatus.DELETED:
            if finding.start_line is not None or finding.end_line is not None:
                return GroundingValidationResult(
                    is_valid=False,
                    rejection_reason=ValidationRejectionReason.FILE_IS_DELETED,
                    details=f"File '{finding.file_path}' was deleted in this pull request; cannot anchor to new revision lines.",
                    file_path=finding.file_path,
                    requested_start_line=finding.start_line,
                    requested_end_line=finding.end_line,
                    is_file_level=False,
                    provenance=provenance,
                )
            if allow_file_level:
                return GroundingValidationResult(
                    is_valid=True,
                    file_path=finding.file_path,
                    is_file_level=True,
                    provenance=provenance,
                )
            return GroundingValidationResult(
                is_valid=False,
                rejection_reason=ValidationRejectionReason.MISSING_LINE_ANCHOR,
                details=f"File '{finding.file_path}' is deleted and file-level findings are disabled.",
                file_path=finding.file_path,
                provenance=provenance,
            )

        # 4. Check file-level findings
        if finding.start_line is None and finding.end_line is None:
            if allow_file_level:
                return GroundingValidationResult(
                    is_valid=True,
                    file_path=finding.file_path,
                    is_file_level=True,
                    provenance=provenance,
                )
            return GroundingValidationResult(
                is_valid=False,
                rejection_reason=ValidationRejectionReason.MISSING_LINE_ANCHOR,
                details="Line-level finding requires start_line and/or end_line anchor.",
                file_path=finding.file_path,
                provenance=provenance,
            )

        # 5. Check line boundary constraints
        start = finding.start_line
        end = finding.end_line

        if (start is not None and start < 1) or (end is not None and end < 1):
            return GroundingValidationResult(
                is_valid=False,
                rejection_reason=ValidationRejectionReason.LINE_OUT_OF_BOUNDS,
                details="Line numbers must be positive 1-indexed integers.",
                file_path=finding.file_path,
                requested_start_line=start,
                requested_end_line=end,
                provenance=provenance,
            )

        if start is not None and end is not None and start > end:
            return GroundingValidationResult(
                is_valid=False,
                rejection_reason=ValidationRejectionReason.INVALID_LINE_RANGE,
                details=f"Start line ({start}) cannot be greater than end line ({end}).",
                file_path=finding.file_path,
                requested_start_line=start,
                requested_end_line=end,
                provenance=provenance,
            )

        range_start = start if start is not None else end
        range_end = end if end is not None else start
        assert range_start is not None and range_end is not None

        target_lines = set(range(range_start, range_end + 1))
        added_set = set(file_diff.added_lines)
        context_set = set(file_diff.context_lines)
        deleted_set = set(file_diff.deleted_lines)

        # Intersections
        intersect_added = sorted(list(target_lines.intersection(added_set)))
        intersect_context = sorted(list(target_lines.intersection(context_set)))
        intersect_deleted = sorted(list(target_lines.intersection(deleted_set)))

        # A: Line is in added/modified lines in the new file -> VALID anchor
        if intersect_added:
            return GroundingValidationResult(
                is_valid=True,
                file_path=finding.file_path,
                requested_start_line=start,
                requested_end_line=end,
                is_file_level=False,
                provenance=provenance,
                anchored_changed_lines=intersect_added,
            )

        # B: Line targets unchanged context lines
        if intersect_context:
            if require_changed_line:
                return GroundingValidationResult(
                    is_valid=False,
                    rejection_reason=ValidationRejectionReason.TARGETS_UNMODIFIED_CONTEXT,
                    details=f"Line range ({range_start}-{range_end}) targets unmodified context lines, not lines modified in this PR.",
                    file_path=finding.file_path,
                    requested_start_line=start,
                    requested_end_line=end,
                    provenance=provenance,
                )
            else:
                return GroundingValidationResult(
                    is_valid=True,
                    file_path=finding.file_path,
                    requested_start_line=start,
                    requested_end_line=end,
                    is_file_level=False,
                    provenance=provenance,
                    anchored_changed_lines=[],
                )

        # C: Line was only present in deleted lines of the old file
        if intersect_deleted:
            return GroundingValidationResult(
                is_valid=False,
                rejection_reason=ValidationRejectionReason.TARGETS_DELETED_LINE,
                details=f"Line range ({range_start}-{range_end}) references deleted line numbers from the base file; these do not exist in the new file.",
                file_path=finding.file_path,
                requested_start_line=start,
                requested_end_line=end,
                provenance=provenance,
            )

        # D: Line falls outside any hunk
        return GroundingValidationResult(
            is_valid=False,
            rejection_reason=ValidationRejectionReason.OUT_OF_HUNK_RANGE,
            details=f"Line range ({range_start}-{range_end}) is not part of any modified hunk in this pull request.",
            file_path=finding.file_path,
            requested_start_line=start,
            requested_end_line=end,
            provenance=provenance,
        )

    def filter_and_validate_findings(
        self,
        findings: List[Union[FindingBase, CandidateFinding]],
        require_changed_line: bool = True,
        allow_file_level: bool = False,
    ) -> Tuple[List[Union[FindingBase, CandidateFinding]], List[GroundingValidationResult]]:
        """
        Filters candidate findings, returning (accepted_findings, all_validation_reports).
        Rejections are logged with clear diagnostic reasons.
        """
        accepted = []
        reports = []

        for f in findings:
            result = self.validate_finding(
                f, require_changed_line=require_changed_line, allow_file_level=allow_file_level
            )
            reports.append(result)
            if result.is_valid:
                accepted.append(f)

        return accepted, reports
