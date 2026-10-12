"""JavaScript and TypeScript Analyzer Plugin implementing BaseLanguageAnalyzer."""
from typing import List, Optional

from src.analyzer.base import (
    BaseLanguageAnalyzer,
    CandidateFinding,
    DiffHunk,
    LanguageReadiness,
    TestRecommendation,
)
from src.parser.models import DiffLine, FileChangeStatus, LineType, ParsedFileDiff, ParsedHunk
from .rules import analyze_javascript_file_diff


class JavaScriptLanguageAnalyzer(BaseLanguageAnalyzer):
    """
    Active JavaScript & TypeScript analysis plugin for Patchwise.
    Implements rules JS001 through JS004 using ESTree AST inspection and line grounding.
    Supports .js, .jsx, .ts, and .tsx file extensions.
    """

    @property
    def language_id(self) -> str:
        return "javascript"

    @property
    def name(self) -> str:
        return "JavaScript / TypeScript"

    @property
    def supported_extensions(self) -> List[str]:
        return [".js", ".jsx", ".ts", ".tsx"]

    @property
    def readiness_status(self) -> LanguageReadiness:
        return LanguageReadiness.IMPLEMENTED_AND_TESTED

    def run_deterministic_checks(
        self,
        file_path: str,
        diff_hunks: List[DiffHunk],
        all_pr_files: Optional[List[str]] = None,
    ) -> List[CandidateFinding]:
        """Run AST and static analysis rules on changed JavaScript/TypeScript file hunks."""
        parsed_hunks: List[ParsedHunk] = []
        added_lines: List[int] = []
        deleted_lines: List[int] = []
        context_lines: List[int] = []

        for h in diff_hunks:
            if isinstance(h, ParsedHunk):
                parsed_hunks.append(h)
                added_lines.extend(h.added_lines)
                deleted_lines.extend(h.deleted_lines)
                context_lines.extend(h.context_lines)
            else:
                parsed_lines: List[DiffLine] = []
                for l in h.lines:
                    prefix = l[0] if l else " "
                    content = l[1:] if len(l) > 1 else ""
                    if prefix == "+":
                        parsed_lines.append(DiffLine(type=LineType.ADDED, content=content))
                    elif prefix == "-":
                        parsed_lines.append(DiffLine(type=LineType.DELETED, content=content))
                    else:
                        parsed_lines.append(DiffLine(type=LineType.CONTEXT, content=content))

                ph = ParsedHunk(
                    old_start=h.old_start,
                    old_length=h.old_length,
                    new_start=h.new_start,
                    new_length=h.new_length,
                    header=h.header,
                    lines=parsed_lines,
                    added_lines=h.added_lines,
                    deleted_lines=h.removed_lines,
                    context_lines=[],
                )
                parsed_hunks.append(ph)
                added_lines.extend(h.added_lines)
                deleted_lines.extend(h.removed_lines)

        file_diff = ParsedFileDiff(
            file_path=file_path,
            status=FileChangeStatus.MODIFIED,
            is_binary=False,
            hunks=parsed_hunks,
            added_lines=sorted(list(set(added_lines))),
            deleted_lines=sorted(list(set(deleted_lines))),
            context_lines=sorted(list(set(context_lines))),
        )

        return analyze_javascript_file_diff(file_diff)

    def get_language_prompt_context(self) -> str:
        return (
            "JavaScript / TypeScript Review Guidelines:\n"
            "- Prohibit arbitrary code execution via eval() or new Function().\n"
            "- Prevent DOM-based XSS: forbid unescaped innerHTML, outerHTML, document.write(), or unvalidated dangerouslySetInnerHTML.\n"
            "- Disallow dynamic shell command interpolation in child_process.exec() or execSync(); require execFile() with parameter arrays.\n"
            "- Prevent SQL injection by requiring parameterized queries instead of string concatenation or template literal interpolation.\n"
            "- Enforce type safety, null/undefined checks, and strict equality (===) where applicable.\n"
        )

    def suggest_tests(
        self, file_path: str, diff_hunks: List[DiffHunk]
    ) -> List[TestRecommendation]:
        return [
            TestRecommendation(
                rationale=f"Add unit tests for modified JavaScript/TypeScript logic in '{file_path}'.",
                test_type="unit",
                sample_test_code="// describe('suite', () => { it('handles edge cases', () => { ... }); });",
            )
        ]
