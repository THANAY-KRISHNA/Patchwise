"""Unit and integration tests for SQL and HiveQL deterministic static analysis rules."""
from typing import List, Tuple
import pytest

from src.analyzer.plugins.sql.rules import analyze_sql_file_diff
from src.parser.models import DiffLine, FileChangeStatus, LineType, ParsedFileDiff, ParsedHunk
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity


def _make_sql_diff(lines_desc: List[Tuple[str, str, int, int]], file_path: str = "query.sql") -> ParsedFileDiff:
    """Helper to build a ParsedFileDiff from line descriptions."""
    diff_lines: List[DiffLine] = []
    added: List[int] = []
    deleted: List[int] = []
    context: List[int] = []

    for marker, content, old_no, new_no in lines_desc:
        if marker == "+":
            l_type = LineType.ADDED
            if new_no is not None:
                added.append(new_no)
        elif marker == "-":
            l_type = LineType.DELETED
            if old_no is not None:
                deleted.append(old_no)
        else:
            l_type = LineType.CONTEXT
            if new_no is not None:
                context.append(new_no)

        diff_lines.append(
            DiffLine(
                type=l_type,
                content=content,
                old_line_number=old_no,
                new_line_number=new_no,
            )
        )

    hunk = ParsedHunk(
        old_start=1,
        old_length=len(deleted) + len(context),
        new_start=1,
        new_length=len(added) + len(context),
        header="@@ -1,1 +1,1 @@",
        lines=diff_lines,
        added_lines=added,
        deleted_lines=deleted,
        context_lines=context,
    )

    return ParsedFileDiff(
        file_path=file_path,
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[hunk],
        added_lines=added,
        deleted_lines=deleted,
        context_lines=context,
    )


# =============================================================================
# SQL001: Missing WHERE Clause Tests
# =============================================================================

def test_sql001_update_without_where_positive():
    diff = _make_sql_diff([
        (" ", "-- Update status", 1, 1),
        ("+", "UPDATE accounts", None, 2),
        ("+", "SET status = 'suspended', active = 0;", None, 3),
        (" ", "-- Next statement", 2, 4),
    ], file_path="migrations/update.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "SQL001"
    assert f.start_line == 2
    assert f.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert f.severity == FindingSeverity.HIGH
    assert "UPDATE" in f.title


def test_sql001_delete_without_where_positive():
    diff = _make_sql_diff([
        (" ", "-- Clean session cache", 1, 1),
        ("+", "DELETE FROM session_tokens;", None, 2),
        (" ", "-- Finished", 2, 3),
    ], file_path="scripts/cleanup.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "SQL001"
    assert f.start_line == 2
    assert f.severity == FindingSeverity.HIGH
    assert "DELETE" in f.title


def test_sql001_safe_update_with_where_negative():
    diff = _make_sql_diff([
        (" ", "BEGIN;", 1, 1),
        ("+", "UPDATE users", None, 2),
        ("+", "SET status = 'active'", None, 3),
        ("+", "WHERE id = 42;", None, 4),
        (" ", "COMMIT;", 2, 5),
    ], file_path="queries/safe_update.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


def test_sql001_safe_delete_with_where_negative():
    diff = _make_sql_diff([
        (" ", "BEGIN;", 1, 1),
        ("+", "DELETE FROM logs", None, 2),
        ("+", "WHERE created_at < NOW() - INTERVAL '30 days';", None, 3),
        (" ", "COMMIT;", 2, 4),
    ], file_path="queries/safe_delete.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


def test_sql001_where_inside_comment_does_not_suppress_positive():
    """A comment mentioning 'where' must not trick the analyzer into thinking WHERE clause is present."""
    diff = _make_sql_diff([
        ("+", "UPDATE users SET status = 'disabled'; -- where id = 123", None, 1),
    ], file_path="queries/tricky.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "SQL001"


def test_sql001_where_inside_string_does_not_suppress_positive():
    """A string literal mentioning 'where' must not trick the analyzer into thinking WHERE clause is present."""
    diff = _make_sql_diff([
        ("+", "UPDATE system_errors SET msg = 'Syntax error near WHERE clause';", None, 1),
    ], file_path="queries/string_where.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "SQL001"


# =============================================================================
# SQL002: Dynamic SQL Construction Tests
# =============================================================================

def test_sql002_execute_immediate_concat_positive():
    diff = _make_sql_diff([
        (" ", "BEGIN", 1, 1),
        ("+", "    EXECUTE IMMEDIATE 'SELECT * FROM ' || user_input_table;", None, 2),
        (" ", "END;", 2, 3),
    ], file_path="procedures/dynamic.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "SQL002"
    assert f.start_line == 2
    assert f.severity == FindingSeverity.HIGH


def test_sql002_sp_executesql_dynamic_positive():
    diff = _make_sql_diff([
        (" ", "-- T-SQL procedure", 1, 1),
        ("+", "EXEC sp_executesql @dynamic_sql;", None, 2),
    ], file_path="tsql/proc.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "SQL002"
    assert findings[0].start_line == 2


def test_sql002_exec_parenthesized_dynamic_positive():
    diff = _make_sql_diff([
        ("+", "EXEC(@cmd_var);", None, 1),
    ], file_path="tsql/exec.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "SQL002"


def test_sql002_execute_immediate_constant_negative():
    diff = _make_sql_diff([
        (" ", "BEGIN", 1, 1),
        ("+", "    EXECUTE IMMEDIATE 'SELECT 1 FROM DUAL';", None, 2),
        (" ", "END;", 2, 3),
    ], file_path="procedures/fixed.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


def test_sql002_exec_constant_literal_negative():
    diff = _make_sql_diff([
        ("+", "EXEC('SELECT 1');", None, 1),
    ], file_path="tsql/safe_exec.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# SQL003: Overly Broad Privileges Tests
# =============================================================================

def test_sql003_grant_all_privileges_positive():
    diff = _make_sql_diff([
        (" ", "-- Permissions", 1, 1),
        ("+", "GRANT ALL PRIVILEGES ON DATABASE production TO app_role;", None, 2),
    ], file_path="auth/grants.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "SQL003"
    assert f.start_line == 2
    assert f.severity == FindingSeverity.HIGH


def test_sql003_grant_with_grant_option_positive():
    diff = _make_sql_diff([
        ("+", "GRANT SELECT ON sensitive_data TO analyst WITH GRANT OPTION;", None, 1),
    ], file_path="auth/delegate.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "SQL003"
    assert f.start_line == 1
    assert "GRANT OPTION" in f.title


def test_sql003_safe_restricted_grant_negative():
    diff = _make_sql_diff([
        ("+", "GRANT SELECT, INSERT ON users TO web_application;", None, 1),
        ("+", "GRANT UPDATE (email, display_name) ON profile TO web_application;", None, 2),
    ], file_path="auth/safe_grants.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# SQL004: Hardcoded Credentials Tests & Secret Masking
# =============================================================================

def test_sql004_create_user_identified_by_positive_and_masked():
    raw_secret = "SuperSecretP@ss123!"
    diff = _make_sql_diff([
        ("+", f"CREATE USER 'service_acc'@'%' IDENTIFIED BY '{raw_secret}';", None, 1),
    ], file_path="admin/users.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "SQL004"
    assert f.start_line == 1
    assert f.severity == FindingSeverity.HIGH
    # Strict secret protection: raw secret must NEVER appear in title or explanation
    assert raw_secret not in f.explanation
    assert raw_secret not in f.title
    assert "***" in f.explanation


def test_sql004_alter_user_with_password_positive():
    diff = _make_sql_diff([
        ("+", "ALTER USER app_svc WITH PASSWORD 'AnotherP@ssword999';", None, 1),
    ], file_path="admin/alter.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "SQL004"
    assert "AnotherP@ssword999" not in findings[0].explanation


def test_sql004_create_user_identified_externally_negative():
    diff = _make_sql_diff([
        ("+", "CREATE USER cloud_user IDENTIFIED EXTERNALLY;", None, 1),
    ], file_path="admin/iam.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


def test_sql004_regular_insert_with_password_column_negative():
    diff = _make_sql_diff([
        ("+", "INSERT INTO settings (k, v) VALUES ('password_min_length', '12');", None, 1),
    ], file_path="seed.sql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# SQL005: HiveQL Operational Data Loss Tests
# =============================================================================

def test_sql005_hive_insert_overwrite_unpartitioned_positive():
    diff = _make_sql_diff([
        (" ", "-- Hive pipeline", 1, 1),
        ("+", "INSERT OVERWRITE TABLE warehouse_events", None, 2),
        ("+", "SELECT * FROM staging_events;", None, 3),
    ], file_path="pipelines/sync.hql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "SQL005"
    assert f.start_line == 2
    assert f.severity == FindingSeverity.LOW
    assert "Unpartitioned" in f.title


def test_sql005_hive_drop_table_purge_positive():
    diff = _make_sql_diff([
        ("+", "DROP TABLE legacy_staging PURGE;", None, 1),
    ], file_path="cleanup.hive")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "SQL005"
    assert f.start_line == 1
    assert "PURGE" in f.title


def test_sql005_hive_insert_overwrite_partitioned_negative():
    diff = _make_sql_diff([
        (" ", "-- Partitioned overwrite is standard Hive pattern", 1, 1),
        ("+", "INSERT OVERWRITE TABLE warehouse_events", None, 2),
        ("+", "PARTITION (event_date = '2026-10-10')", None, 3),
        ("+", "SELECT * FROM staging_events;", None, 4),
    ], file_path="pipelines/safe_sync.hql")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


def test_sql005_hive_insert_into_negative():
    diff = _make_sql_diff([
        ("+", "INSERT INTO TABLE warehouse_events SELECT * FROM staging_events;", None, 1),
    ], file_path="pipelines/append.q")
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# Multi-Hunk Line Mapping & Edge Case Robustness
# =============================================================================

def test_sql_multi_hunk_line_mapping():
    hunk1_lines = [
        DiffLine(type=LineType.CONTEXT, content="-- Hunk 1", old_line_number=1, new_line_number=1),
        DiffLine(type=LineType.ADDED, content="UPDATE users SET active = 0;", old_line_number=None, new_line_number=2),
    ]
    hunk2_lines = [
        DiffLine(type=LineType.CONTEXT, content="-- Hunk 2", old_line_number=40, new_line_number=40),
        DiffLine(type=LineType.ADDED, content="GRANT ALL PRIVILEGES ON *.* TO 'root'@'%';", old_line_number=None, new_line_number=41),
    ]
    hunk1 = ParsedHunk(old_start=1, old_length=1, new_start=1, new_length=2, header="@@ -1,1 +1,2 @@", lines=hunk1_lines, added_lines=[2], deleted_lines=[], context_lines=[1])
    hunk2 = ParsedHunk(old_start=40, old_length=1, new_start=40, new_length=2, header="@@ -40,1 +40,2 @@", lines=hunk2_lines, added_lines=[41], deleted_lines=[], context_lines=[40])

    diff = ParsedFileDiff(
        file_path="db/script.sql",
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[hunk1, hunk2],
        added_lines=[2, 41],
        deleted_lines=[],
        context_lines=[1, 40],
    )
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 2
    rule_map = {f.start_line: f.rule_id for f in findings}
    assert rule_map == {2: "SQL001", 41: "SQL003"}


def test_empty_sql_diff_handling():
    diff = ParsedFileDiff(
        file_path="empty.sql",
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[],
        added_lines=[],
        deleted_lines=[],
        context_lines=[],
    )
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


def test_binary_sql_diff_handling():
    diff = ParsedFileDiff(
        file_path="dump.sql",
        status=FileChangeStatus.MODIFIED,
        is_binary=True,
        hunks=[],
        added_lines=[],
        deleted_lines=[],
        context_lines=[],
    )
    findings = analyze_sql_file_diff(diff)
    assert len(findings) == 0


def test_sql_syntax_error_tolerance():
    diff = _make_sql_diff([
        ("+", "@@@ ??? <<<< ;;; ::: SELECT FROM WHERE WHERE", None, 1),
    ], file_path="corrupt.sql")
    # Must not raise an exception
    findings = analyze_sql_file_diff(diff)
    assert isinstance(findings, list)
