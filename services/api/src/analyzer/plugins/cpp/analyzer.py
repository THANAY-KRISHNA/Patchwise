"""C and C++ Analyzer Plugin implementing BaseLanguageAnalyzer."""
from typing import List, Optional

from src.analyzer.base import (
    BaseLanguageAnalyzer,
    CandidateFinding,
    DiffHunk,
    LanguageReadiness,
    TestRecommendation,
)
from src.parser.models import DiffLine, FileChangeStatus, LineType, ParsedFileDiff, ParsedHunk
from .rules import analyze_cpp_file_diff

CPP_EXTENSIONS = [
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".cxx",
    ".hh",
    ".hpp",
    ".hxx",
]


class CppLanguageAnalyzer(BaseLanguageAnalyzer):
    """
    Active C and C++ static analysis plugin for Patchwise.
    Implements deterministic token-based call and syntax-aware rules CC001 through CC004
    with exact diff line grounding.
    """

    @property
    def language_id(self) -> str:
        return "cpp"

    @property
    def name(self) -> str:
        return "C / C++"

    @property
    def supported_extensions(self) -> List[str]:
        return CPP_EXTENSIONS

    @property
    def readiness_status(self) -> LanguageReadiness:
        return LanguageReadiness.IMPLEMENTED_AND_TESTED

    def run_deterministic_checks(
        self,
        file_path: str,
        diff_hunks: List[DiffHunk],
        all_pr_files: Optional[List[str]] = None,
    ) -> List[CandidateFinding]:
        """Run token-based syntax checks on changed C/C++ file hunks."""
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

        return analyze_cpp_file_diff(file_diff)

    def get_language_prompt_context(self) -> str:
        return (
            "C and C++ Review Guidelines:\n"
            "- Prevent buffer overflows: replace unbounded string APIs (gets, strcpy, strcat, sprintf) with bounded alternatives (fgets, strncpy, snprintf, std::string).\n"
            "- Prevent format string vulnerabilities: ensure the format specifier in printf-family functions is a compile-time string literal, never a variable.\n"
            "- Prevent shell command injection: avoid system() and popen() with dynamic strings; prefer execve() with discrete argument vectors.\n"
            "- Prevent temporary file race conditions: replace mktemp/tmpnam with mkstemp() or std::filesystem APIs.\n"
            "- Enforce memory safety and RAII (unique_ptr, shared_ptr) over manual malloc/free or raw new/delete.\n"
        )

    def suggest_tests(
        self, file_path: str, diff_hunks: List[DiffHunk]
    ) -> List[TestRecommendation]:
        return [
            TestRecommendation(
                rationale=f"Add unit tests (e.g. GoogleTest or Catch2) for modified C/C++ functionality in '{file_path}'.",
                test_type="unit",
                sample_test_code="TEST(FeatureTest, HandlesBoundaryInputs) {\n    EXPECT_TRUE(ExecuteFeature());\n}",
            )
        ]
