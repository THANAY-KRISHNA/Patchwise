"""Java Analyzer Plugin implementing BaseLanguageAnalyzer."""
from typing import List, Optional

from src.analyzer.base import (
    BaseLanguageAnalyzer,
    CandidateFinding,
    DiffHunk,
    LanguageReadiness,
    TestRecommendation,
)
from src.parser.models import DiffLine, FileChangeStatus, LineType, ParsedFileDiff, ParsedHunk
from .rules import analyze_java_file_diff


class JavaLanguageAnalyzer(BaseLanguageAnalyzer):
    """
    Active Java static analysis plugin for Patchwise.
    Implements deterministic AST rules JV001 through JV004 with exact diff line grounding.
    Supports .java files.
    """

    @property
    def language_id(self) -> str:
        return "java"

    @property
    def name(self) -> str:
        return "Java"

    @property
    def supported_extensions(self) -> List[str]:
        return [".java"]

    @property
    def readiness_status(self) -> LanguageReadiness:
        return LanguageReadiness.IMPLEMENTED_AND_TESTED

    def run_deterministic_checks(
        self,
        file_path: str,
        diff_hunks: List[DiffHunk],
        all_pr_files: Optional[List[str]] = None,
    ) -> List[CandidateFinding]:
        """Run AST and static analysis rules on changed Java file hunks."""
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
                        l_type = LineType.ADDED
                    elif prefix == "-":
                        l_type = LineType.DELETED
                    else:
                        l_type = LineType.CONTEXT

                    parsed_lines.append(
                        DiffLine(
                            type=l_type,
                            content=content,
                            old_line_number=None,
                            new_line_number=None,
                        )
                    )

                parsed_hunk = ParsedHunk(
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
                parsed_hunks.append(parsed_hunk)
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

        return analyze_java_file_diff(file_diff)

    def get_language_prompt_context(self) -> str:
        return (
            "Java Review Guidelines:\n"
            "- Disallow unsafe native deserialization via ObjectInputStream.readObject() without lookahead filtering (ObjectInputFilter).\n"
            "- Prevent OS command injection: disallow dynamic string concatenation in Runtime.getRuntime().exec() or ProcessBuilder.\n"
            "- Prevent SQL injection: enforce parameterized PreparedStatement queries with '?' placeholders instead of string concatenation.\n"
            "- Prevent path traversal: validate file paths using Path.normalize() and verify canonical path containment (startsWith base directory).\n"
            "- Ensure resource cleanup using try-with-resources blocks (AutoCloseable).\n"
        )

    def suggest_tests(
        self, file_path: str, diff_hunks: List[DiffHunk]
    ) -> List[TestRecommendation]:
        return [
            TestRecommendation(
                rationale=f"Add JUnit 5 unit or integration tests for modified Java logic in '{file_path}'.",
                test_type="unit",
                sample_test_code="@Test\nvoid testFeatureExecution() {\n    // Assert expected behavior and edge cases\n}",
            )
        ]
