"""Curated and Versioned Benchmark Dataset Fixtures for SQL and HiveQL (v1.0.0).

Contains 20 labelled code diffs with ground-truth expected findings for deterministic rules
SQL001–SQL005 across SQL and HiveQL files (.sql, .hql, .hive, .q), clean negative examples (true negatives),
edge cases, and malformed inputs.
"""
from typing import List
from ..schemas.findings import FindingProvenance
from .models import BenchmarkCase, BenchmarkDataset, ExpectedFinding

DATASET_VERSION_SQL = "v1.0.0"
DATASET_NAME_SQL = "patchwise-sql-deterministic-benchmark"


def get_sql_benchmark_dataset() -> BenchmarkDataset:
    """Builds and returns the frozen SQL and HiveQL benchmark dataset (v1.0.0)."""
    cases: List[BenchmarkCase] = [
        # =====================================================================
        # Category 1: Deterministic Rule Positives (SQL001 - SQL005)
        # =====================================================================
        BenchmarkCase(
            id="sql001_update_unbounded_positive",
            name="SQL001: Unbounded UPDATE without WHERE clause",
            description="Broad UPDATE statement without a WHERE clause modifies all records in the table.",
            diff_patch="""@@ -1,1 +1,4 @@
 -- Bulk status update
+UPDATE users
+SET active = 0, status = 'archived';
 -- Complete
""",
            target_file="scripts/update_users.sql",
            all_pr_files=["scripts/update_users.sql"],
            language="sql",
            expected_findings=[
                ExpectedFinding(
                    rule_id="SQL001",
                    file_path="scripts/update_users.sql",
                    start_line=2,
                    end_line=2,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Unbounded UPDATE statement without WHERE clause",
                )
            ],
            tags=["sql001", "data_loss", "positive"],
        ),
        BenchmarkCase(
            id="sql001_delete_unbounded_positive",
            name="SQL001: Unbounded DELETE without WHERE clause",
            description="Broad DELETE statement without a WHERE clause purges all rows from the target table.",
            diff_patch="""@@ -10,1 +10,3 @@
 -- Purge old sessions
+DELETE FROM auth_tokens;
 -- Return count
""",
            target_file="cleanup/purge_sessions.sql",
            all_pr_files=["cleanup/purge_sessions.sql"],
            language="sql",
            expected_findings=[
                ExpectedFinding(
                    rule_id="SQL001",
                    file_path="cleanup/purge_sessions.sql",
                    start_line=11,
                    end_line=11,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Unbounded DELETE statement without WHERE clause",
                )
            ],
            tags=["sql001", "data_loss", "positive"],
        ),
        BenchmarkCase(
            id="sql002_execute_immediate_concat_positive",
            name="SQL002: Dynamic SQL via EXECUTE IMMEDIATE string concatenation",
            description="Executing dynamic query constructed by concatenating untrusted table identifier.",
            diff_patch="""@@ -5,1 +5,4 @@
 BEGIN
+    EXECUTE IMMEDIATE 'SELECT * FROM ' || user_input_table;
 END;
""",
            target_file="sp/exec_dynamic.sql",
            all_pr_files=["sp/exec_dynamic.sql"],
            language="sql",
            expected_findings=[
                ExpectedFinding(
                    rule_id="SQL002",
                    file_path="sp/exec_dynamic.sql",
                    start_line=6,
                    end_line=6,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Dynamic SQL via string concatenation in EXECUTE IMMEDIATE",
                )
            ],
            tags=["sql002", "injection", "positive"],
        ),
        BenchmarkCase(
            id="sql002_sp_executesql_dynamic_positive",
            name="SQL002: Dynamic SQL via sp_executesql variable parameter",
            description="Executing unparameterized dynamic query variable via sp_executesql.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Run dynamic report
+EXEC sp_executesql @query_statement;
""",
            target_file="tsql/reports.sql",
            all_pr_files=["tsql/reports.sql"],
            language="sql",
            expected_findings=[
                ExpectedFinding(
                    rule_id="SQL002",
                    file_path="tsql/reports.sql",
                    start_line=2,
                    end_line=2,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Dynamic query execution via sp_executesql variable",
                )
            ],
            tags=["sql002", "injection", "positive"],
        ),
        BenchmarkCase(
            id="sql003_grant_all_privileges_positive",
            name="SQL003: Overly broad privilege grant (GRANT ALL PRIVILEGES)",
            description="Granting ALL PRIVILEGES on database violates the principle of least privilege.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Superuser access
+GRANT ALL PRIVILEGES ON DATABASE prod_db TO dev_role;
""",
            target_file="db/setup_permissions.sql",
            all_pr_files=["db/setup_permissions.sql"],
            language="sql",
            expected_findings=[
                ExpectedFinding(
                    rule_id="SQL003",
                    file_path="db/setup_permissions.sql",
                    start_line=2,
                    end_line=2,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Excessive privileges granted via GRANT ALL PRIVILEGES",
                )
            ],
            tags=["sql003", "privilege", "positive"],
        ),
        BenchmarkCase(
            id="sql003_grant_with_grant_option_positive",
            name="SQL003: Dangerous WITH GRANT OPTION privilege escalation",
            description="Granting rights WITH GRANT OPTION allows non-admin users to re-grant permissions.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Delegate administrative rights
+GRANT SELECT, INSERT ON customer_data TO partner_role WITH GRANT OPTION;
""",
            target_file="security/delegation.sql",
            all_pr_files=["security/delegation.sql"],
            language="sql",
            expected_findings=[
                ExpectedFinding(
                    rule_id="SQL003",
                    file_path="security/delegation.sql",
                    start_line=2,
                    end_line=2,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Granting permissions WITH GRANT OPTION",
                )
            ],
            tags=["sql003", "privilege", "positive"],
        ),
        BenchmarkCase(
            id="sql004_create_user_hardcoded_pw_positive",
            name="SQL004: Hardcoded credential in CREATE USER statement",
            description="Creating database user account with plaintext password literal in SQL source.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Add service account
+CREATE USER 'etl_worker'@'%' IDENTIFIED BY 'SuperSecretP@ss123';
""",
            target_file="provisioning/new_service_user.sql",
            all_pr_files=["provisioning/new_service_user.sql"],
            language="sql",
            expected_findings=[
                ExpectedFinding(
                    rule_id="SQL004",
                    file_path="provisioning/new_service_user.sql",
                    start_line=2,
                    end_line=2,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Hardcoded credential in CREATE USER statement",
                )
            ],
            tags=["sql004", "credentials", "positive"],
        ),
        BenchmarkCase(
            id="sql004_alter_user_hardcoded_pw_positive",
            name="SQL004: Hardcoded credential in ALTER USER statement",
            description="Altering database user password with plaintext literal in SQL migration script.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Reset analyst password
+ALTER USER analyst_service WITH PASSWORD 'ProdSecret2026!';
""",
            target_file="provisioning/rotate_key.sql",
            all_pr_files=["provisioning/rotate_key.sql"],
            language="sql",
            expected_findings=[
                ExpectedFinding(
                    rule_id="SQL004",
                    file_path="provisioning/rotate_key.sql",
                    start_line=2,
                    end_line=2,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Hardcoded credential in ALTER USER statement",
                )
            ],
            tags=["sql004", "credentials", "positive"],
        ),
        BenchmarkCase(
            id="sql005_hive_insert_overwrite_unpartitioned_positive",
            name="SQL005: Unpartitioned HiveQL INSERT OVERWRITE TABLE",
            description="Unpartitioned INSERT OVERWRITE replaces entire table contents without partition boundary.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Overwrite reporting table
+INSERT OVERWRITE TABLE daily_aggregates SELECT user_id, count(*) FROM raw_events;
""",
            target_file="etl/daily_aggregate.hql",
            all_pr_files=["etl/daily_aggregate.hql"],
            language="sql",
            expected_findings=[
                ExpectedFinding(
                    rule_id="SQL005",
                    file_path="etl/daily_aggregate.hql",
                    start_line=2,
                    end_line=2,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Unpartitioned INSERT OVERWRITE TABLE in HiveQL",
                )
            ],
            tags=["sql005", "hive", "data_loss", "positive"],
        ),
        BenchmarkCase(
            id="sql005_hive_drop_table_purge_positive",
            name="SQL005: HiveQL DROP TABLE PURGE (bypasses trash)",
            description="Specifying PURGE bypasses the Hive Trash folder, permanently deleting table data.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Drop scratch table immediately
+DROP TABLE staging_raw_events PURGE;
""",
            target_file="etl/cleanup_staging.hive",
            all_pr_files=["etl/cleanup_staging.hive"],
            language="sql",
            expected_findings=[
                ExpectedFinding(
                    rule_id="SQL005",
                    file_path="etl/cleanup_staging.hive",
                    start_line=2,
                    end_line=2,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="HiveQL DROP TABLE with PURGE bypassing trash retention",
                )
            ],
            tags=["sql005", "hive", "data_loss", "positive"],
        ),
        # =====================================================================
        # Category 2: Clean Negatives and Edge Cases (True Negatives)
        # =====================================================================
        BenchmarkCase(
            id="sql001_safe_update_with_where_negative",
            name="Clean Negative: Scoped UPDATE with WHERE clause",
            description="UPDATE statement properly scoped with a specific WHERE clause targeting a single ID.",
            diff_patch="""@@ -1,1 +1,4 @@
 -- Scoped update
+UPDATE users
+SET active = 1
+WHERE user_id = 42;
""",
            target_file="scripts/safe_update.sql",
            all_pr_files=["scripts/safe_update.sql"],
            language="sql",
            expected_findings=[],
            is_negative_case=True,
            tags=["sql001", "clean_negative", "true_negative"],
        ),
        BenchmarkCase(
            id="sql001_safe_delete_with_where_negative",
            name="Clean Negative: Scoped DELETE with WHERE clause",
            description="DELETE statement properly constrained by an indexed token lookup WHERE clause.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Delete single session
+DELETE FROM sessions WHERE token = 'valid_session_token';
""",
            target_file="scripts/safe_delete.sql",
            all_pr_files=["scripts/safe_delete.sql"],
            language="sql",
            expected_findings=[],
            is_negative_case=True,
            tags=["sql001", "clean_negative", "true_negative"],
        ),
        BenchmarkCase(
            id="sql002_execute_immediate_constant_negative",
            name="Clean Negative: Static literal in EXECUTE IMMEDIATE",
            description="EXECUTE IMMEDIATE with a fixed static string literal query is completely safe.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Constant literal query
+EXECUTE IMMEDIATE 'SELECT 1 FROM DUAL';
""",
            target_file="sp/safe_dyn.sql",
            all_pr_files=["sp/safe_dyn.sql"],
            language="sql",
            expected_findings=[],
            is_negative_case=True,
            tags=["sql002", "clean_negative", "true_negative"],
        ),
        BenchmarkCase(
            id="sql002_exec_constant_literal_negative",
            name="Clean Negative: Static literal in EXEC()",
            description="T-SQL EXEC() containing a constant query literal without variables or concatenation.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Fixed query
+EXEC('SELECT @@SERVERNAME');
""",
            target_file="tsql/safe_exec.sql",
            all_pr_files=["tsql/safe_exec.sql"],
            language="sql",
            expected_findings=[],
            is_negative_case=True,
            tags=["sql002", "clean_negative", "true_negative"],
        ),
        BenchmarkCase(
            id="sql003_safe_restricted_grant_negative",
            name="Clean Negative: Principle of least privilege grant",
            description="GRANT SELECT, INSERT on a specific table to a service role without administrative flags.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Least privilege
+GRANT SELECT, INSERT ON logs TO audit_reader;
""",
            target_file="security/restricted_grant.sql",
            all_pr_files=["security/restricted_grant.sql"],
            language="sql",
            expected_findings=[],
            is_negative_case=True,
            tags=["sql003", "clean_negative", "true_negative"],
        ),
        BenchmarkCase(
            id="sql004_create_user_identified_externally_negative",
            name="Clean Negative: External authentication (IDENTIFIED EXTERNALLY)",
            description="CREATE USER configured with external / IAM identity provider without credentials.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- IAM authentication
+CREATE USER iam_app_service IDENTIFIED EXTERNALLY;
""",
            target_file="provisioning/external_auth.sql",
            all_pr_files=["provisioning/external_auth.sql"],
            language="sql",
            expected_findings=[],
            is_negative_case=True,
            tags=["sql004", "clean_negative", "true_negative"],
        ),
        BenchmarkCase(
            id="sql005_hive_insert_overwrite_partitioned_negative",
            name="Clean Negative: Partitioned HiveQL INSERT OVERWRITE",
            description="HiveQL INSERT OVERWRITE scoped to an explicit PARTITION specifier avoids full table loss.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Partitioned safe overwrite
+INSERT OVERWRITE TABLE events PARTITION (dt = '2026-10-13') SELECT * FROM raw_events;
""",
            target_file="etl/partitioned_load.q",
            all_pr_files=["etl/partitioned_load.q"],
            language="sql",
            expected_findings=[],
            is_negative_case=True,
            tags=["sql005", "hive", "clean_negative", "true_negative"],
        ),
        BenchmarkCase(
            id="sql005_hive_insert_into_negative",
            name="Clean Negative: Standard append INSERT INTO TABLE",
            description="HiveQL standard append INSERT INTO does not overwrite or destroy existing records.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Standard append
+INSERT INTO TABLE clickstream SELECT * FROM kafka_stream;
""",
            target_file="etl/append_load.hql",
            all_pr_files=["etl/append_load.hql"],
            language="sql",
            expected_findings=[],
            is_negative_case=True,
            tags=["sql005", "hive", "clean_negative", "true_negative"],
        ),
        BenchmarkCase(
            id="sql_syntax_error_tolerance_negative",
            name="Edge Case: Incomplete / malformed SQL statement",
            description="Malformed syntax fragments must be tolerated gracefully without crashing or false positives.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Malformed incomplete statement
+SELECT FROM WHERE ORDER ;;; (((
""",
            target_file="migrations/malformed.sql",
            all_pr_files=["migrations/malformed.sql"],
            language="sql",
            expected_findings=[],
            is_negative_case=True,
            tags=["syntax_error", "edge_case", "clean_negative"],
        ),
        BenchmarkCase(
            id="sql_comments_only_negative",
            name="Edge Case: SQL comments mentioning dangerous keywords",
            description="Diff adding comments containing 'UPDATE users' or 'WHERE' must not be flagged.",
            diff_patch="""@@ -1,1 +1,3 @@
 -- Migration notes
+-- UPDATE users SET active = 0 without where in a comment
""",
            target_file="notes/migration_notes.sql",
            all_pr_files=["notes/migration_notes.sql"],
            language="sql",
            expected_findings=[],
            is_negative_case=True,
            tags=["comments", "edge_case", "clean_negative"],
        ),
    ]

    return BenchmarkDataset(
        name=DATASET_NAME_SQL,
        version=DATASET_VERSION_SQL,
        description="Frozen evaluation benchmark dataset for Patchwise SQL and HiveQL static rules (v1.0.0)",
        cases=cases,
    )
