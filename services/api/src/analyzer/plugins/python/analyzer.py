"""Python Analyzer Plugin implementing BaseLanguageAnalyzer."""
from typing import List, Optional
from src.parser.models import DiffLine, FileChangeStatus, LineType, ParsedFileDiff, ParsedHunk
from src.analyzer.base import BaseLanguageAnalyzer, CandidateFinding, DiffHunk, LanguageReadiness, TestRecommendation
from .rules import analyze_python_file_diff


class PythonLanguageAnalyzer(BaseLanguageAnalyzer):
    """
    Active Python analysis plugin for Patchwise.
    Implements rules PY001 through PY005 using AST inspection and line grounding.
    """

    @property
    def language_id(self) -> str:
        return "python"

    @property
    def name(self) -> str:
        return "Python"

    @property
    def supported_extensions(self) -> List[str]:
        return [".py"]

    @property
    def readiness_status(self) -> LanguageReadiness:
        return LanguageReadiness.IMPLEMENTED_AND_TESTED

    def run_deterministic_checks(
        self,
        file_path: str,
        diff_hunks: List[DiffHunk],
        all_pr_files: Optional[List[str]] = None,
    ) -> List[CandidateFinding]:
        """Run AST and static analysis rules on changed Python file hunks."""
        # Convert DiffHunk objects into ParsedHunk objects if needed
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
                # DiffHunk from base.py
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

        return analyze_python_file_diff(file_diff, all_pr_files=all_pr_files)

    def get_language_prompt_context(self) -> str:
        return (
            "Python 3.11+ Review Guidelines:\n"
            "- Check for type hints and None safety on nullable arguments.\n"
            "- Verify that resources (files, sockets, DB connections) use context managers ('with' statements).\n"
            "- Beware of mutable default values in function definitions (e.g., list/dict).\n"
            "- Avoid bare except clauses that catch BaseException.\n"
            "- Enforce parameterized queries to avoid SQL injection.\n"
        )

    def suggest_tests(
        self, file_path: str, diff_hunks: List[DiffHunk]
    ) -> List[TestRecommendation]:
        """Generate test recommendations based on modified code constructs."""
        recommendations: List[TestRecommendation] = []
        for h in diff_hunks:
            for line in h.lines:
                if line.startswith("+") and "def " in line:
                    func_name = line.split("def ")[1].split("(")[0].strip()
                    recommendations.append(
                        TestRecommendation(
                            target_function=func_name,
                            test_type="unit",
                            rationale=f"New or updated function '{func_name}' should have unit tests covering normal and boundary cases.",
                            sample_test_code=f"def test_{func_name}_success():\n    # Test behavior of {func_name}\n    pass\n",
                        )
                    )
        return recommendations
