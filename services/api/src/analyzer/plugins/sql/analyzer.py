"""SQL and HiveQL Analyzer Plugin implementing BaseLanguageAnalyzer."""
from typing import List, Optional

from src.analyzer.base import (
    BaseLanguageAnalyzer,
    CandidateFinding,
    DiffHunk,
    LanguageReadiness,
    TestRecommendation,
)
from src.parser.models import DiffLine, FileChangeStatus, LineType, ParsedFileDiff, ParsedHunk
from .rules import analyze_sql_file_diff

SQL_EXTENSIONS = [
    ".sql",
    ".hql",
    ".hive",
    ".q",
]


class SqlLanguageAnalyzer(BaseLanguageAnalyzer):
    """
    Active SQL and HiveQL static analysis plugin for Patchwise.
    Implements deterministic token-based rules SQL001 through SQL005
    with exact diff line grounding.
    """

    @property
    def language_id(self) -> str:
        return "sql"

    @property
    def name(self) -> str:
        return "SQL / HiveQL"

    @property
    def supported_extensions(self) -> List[str]:
        return SQL_EXTENSIONS

    @property
    def readiness_status(self) -> LanguageReadiness:
        return LanguageReadiness.IMPLEMENTED_AND_TESTED

    def run_deterministic_checks(
        self,
        file_path: str,
        diff_hunks: List[DiffHunk],
        all_pr_files: Optional[List[str]] = None,
    ) -> List[CandidateFinding]:
        """Run token-based syntax checks on changed SQL/HiveQL file hunks."""
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

        return analyze_sql_file_diff(file_diff)

    def get_language_prompt_context(self) -> str:
        return (
            "SQL & HiveQL Review Guidelines:\n"
            "- Prevent unbounded data modification: ensure UPDATE and DELETE statements always include an explicit, restrictive WHERE clause.\n"
            "- Prevent SQL injection: avoid dynamic SQL execution (EXECUTE IMMEDIATE, sp_executesql, EXEC) with concatenated strings; use parameterized queries with bind variables.\n"
            "- Enforce least privilege: avoid GRANT ALL PRIVILEGES and WITH GRANT OPTION unless strictly necessary for administrative roles.\n"
            "- Prevent credential leaks: never commit plaintext database passwords or credentials in CREATE USER / ALTER USER statements.\n"
            "- Prevent Hive data loss: avoid unpartitioned INSERT OVERWRITE TABLE and DROP TABLE PURGE unless intentional full table replacement is documented.\n"
        )

    def suggest_tests(
        self, file_path: str, diff_hunks: List[DiffHunk]
    ) -> List[TestRecommendation]:
        return [
            TestRecommendation(
                rationale=f"Add migration verification and database rollback tests for SQL script '{file_path}'.",
                test_type="integration",
                sample_test_code="-- Verify migration idempotency\nBEGIN TRANSACTION;\n-- Run modified statements\nROLLBACK;",
            )
        ]
