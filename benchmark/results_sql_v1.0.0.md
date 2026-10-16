# Patchwise Benchmark Evaluation Report

## 1. Run Metadata

- **Dataset:** `patchwise-sql-deterministic-benchmark` (`v1.0.0`)
- **Engine Version:** `0.1.0`
- **Active Provider:** `none`
- **Run Timestamp (UTC):** `2026-10-13 18:25:10 UTC`
- **Total Fixtures Evaluated:** `20`

## 2. Overall Performance Metrics

| Metric | Measured Value | Unit / Definition |
| :--- | :--- | :--- |
| **Pass Rate** | **100.0%** | Passed Fixtures (20/20) |
| **True Positives (TP)** | 10 | Ground-truth defects correctly detected (Finding level) |
| **False Positives (FP)** | 0 | Spurious findings on code (Finding level) |
| **False Negatives (FN)** | 0 | Expected defects missed by analyzer (Finding level) |
| **True Negatives (TN)** | 10 | Clean/edge fixtures correctly producing 0 findings (Case level) |
| **Precision** | **1.0000** (100.0%) | TP / (TP + FP) at finding level |
| **Recall** | **1.0000** (100.0%) | TP / (TP + FN) at finding level |
| **F1 Score** | **1.0000** | Harmonic mean of Precision & Recall (Finding level) |
| **False Positive Rate** | 0.0000 (0.0%) | FP cases / (FP cases + TN cases) at case level |

## 3. Latency Statistics

- **Mean Latency per Fixture:** `4.28 ms`
- **Median Latency:** `1.85 ms`
- **95th Percentile (p95):** `2.88 ms`
- **Total Benchmark Wall Time:** `85.62 ms`

## 4. Per-Rule Breakdown

| Rule ID | Category / Target | TP | FP | FN | Precision | Recall | F1 Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **SQL001** | Static rule | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **SQL002** | Static rule | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **SQL003** | Static rule | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **SQL004** | Static rule | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **SQL005** | Static rule | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

## 5. Case-by-Case Execution Outcomes

| Status | Case ID | Name | Expected | Actual | Latency | Outcome Details |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| PASSED | `sql001_update_unbounded_positive` | SQL001: Unbounded UPDATE without WHERE clause | 1 | 1 | 49.4 ms | Matched all ground-truth expectations. |
| PASSED | `sql001_delete_unbounded_positive` | SQL001: Unbounded DELETE without WHERE clause | 1 | 1 | 2.37 ms | Matched all ground-truth expectations. |
| PASSED | `sql002_execute_immediate_concat_positive` | SQL002: Dynamic SQL via EXECUTE IMMEDIATE string concatenation | 1 | 1 | 2.07 ms | Matched all ground-truth expectations. |
| PASSED | `sql002_sp_executesql_dynamic_positive` | SQL002: Dynamic SQL via sp_executesql variable parameter | 1 | 1 | 2.62 ms | Matched all ground-truth expectations. |
| PASSED | `sql003_grant_all_privileges_positive` | SQL003: Overly broad privilege grant (GRANT ALL PRIVILEGES) | 1 | 1 | 1.9 ms | Matched all ground-truth expectations. |
| PASSED | `sql003_grant_with_grant_option_positive` | SQL003: Dangerous WITH GRANT OPTION privilege escalation | 1 | 1 | 1.81 ms | Matched all ground-truth expectations. |
| PASSED | `sql004_create_user_hardcoded_pw_positive` | SQL004: Hardcoded credential in CREATE USER statement | 1 | 1 | 1.93 ms | Matched all ground-truth expectations. |
| PASSED | `sql004_alter_user_hardcoded_pw_positive` | SQL004: Hardcoded credential in ALTER USER statement | 1 | 1 | 2.88 ms | Matched all ground-truth expectations. |
| PASSED | `sql005_hive_insert_overwrite_unpartitioned_positive` | SQL005: Unpartitioned HiveQL INSERT OVERWRITE TABLE | 1 | 1 | 1.95 ms | Matched all ground-truth expectations. |
| PASSED | `sql005_hive_drop_table_purge_positive` | SQL005: HiveQL DROP TABLE PURGE (bypasses trash) | 1 | 1 | 1.75 ms | Matched all ground-truth expectations. |
| PASSED | `sql001_safe_update_with_where_negative` | Clean Negative: Scoped UPDATE with WHERE clause | 0 | 0 | 1.72 ms | Matched all ground-truth expectations. |
| PASSED | `sql001_safe_delete_with_where_negative` | Clean Negative: Scoped DELETE with WHERE clause | 0 | 0 | 2.28 ms | Matched all ground-truth expectations. |
| PASSED | `sql002_execute_immediate_constant_negative` | Clean Negative: Static literal in EXECUTE IMMEDIATE | 0 | 0 | 1.7 ms | Matched all ground-truth expectations. |
| PASSED | `sql002_exec_constant_literal_negative` | Clean Negative: Static literal in EXEC() | 0 | 0 | 1.44 ms | Matched all ground-truth expectations. |
| PASSED | `sql003_safe_restricted_grant_negative` | Clean Negative: Principle of least privilege grant | 0 | 0 | 1.37 ms | Matched all ground-truth expectations. |
| PASSED | `sql004_create_user_identified_externally_negative` | Clean Negative: External authentication (IDENTIFIED EXTERNALLY) | 0 | 0 | 1.74 ms | Matched all ground-truth expectations. |
| PASSED | `sql005_hive_insert_overwrite_partitioned_negative` | Clean Negative: Partitioned HiveQL INSERT OVERWRITE | 0 | 0 | 2.37 ms | Matched all ground-truth expectations. |
| PASSED | `sql005_hive_insert_into_negative` | Clean Negative: Standard append INSERT INTO TABLE | 0 | 0 | 1.55 ms | Matched all ground-truth expectations. |
| PASSED | `sql_syntax_error_tolerance_negative` | Edge Case: Incomplete / malformed SQL statement | 0 | 0 | 1.38 ms | Matched all ground-truth expectations. |
| PASSED | `sql_comments_only_negative` | Edge Case: SQL comments mentioning dangerous keywords | 0 | 0 | 1.39 ms | Matched all ground-truth expectations. |

## 6. Evaluation Methodology & Known Limitations

1. **Curated Benchmark Scope:** This evaluation measures performance against versioned synthetic and curated code-diff fixtures. It validates parser correctness, AST matching, and grounding validation, but does not prove real-world bug-detection accuracy across arbitrary unseen repositories.
2. **Evaluation Units:** Precision, Recall, and F1 are evaluated at the Finding level. False Positive Rate (FPR) and True Negatives (TN) are evaluated at the Case level on ground-truth negative fixtures.
3. **Zero Denominator Handling:** When metric denominators evaluate to zero, measurements are reported explicitly as `N/A` rather than manufactured numbers.
4. **Truth-in-Advertising:** Measurements in this report reflect actual code execution without simulated or hardcoded results.