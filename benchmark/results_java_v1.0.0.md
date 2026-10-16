# Patchwise Benchmark Evaluation Report

## 1. Run Metadata

- **Dataset:** `patchwise-java-deterministic-benchmark` (`v1.0.0`)
- **Engine Version:** `0.1.0`
- **Active Provider:** `none`
- **Run Timestamp (UTC):** `2026-10-13 16:53:27 UTC`
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

- **Mean Latency per Fixture:** `6.33 ms`
- **Median Latency:** `3.08 ms`
- **95th Percentile (p95):** `5.22 ms`
- **Total Benchmark Wall Time:** `126.7 ms`

## 4. Per-Rule Breakdown

| Rule ID | Category / Target | TP | FP | FN | Precision | Recall | F1 Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **JV001** | Static rule | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **JV002** | Static rule | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **JV003** | Static rule | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **JV004** | Static rule | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

## 5. Case-by-Case Execution Outcomes

| Status | Case ID | Name | Expected | Actual | Latency | Outcome Details |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| PASSED | `jv001_read_object_positive` | JV001: Potentially unsafe Java deserialization via readObject() | 1 | 1 | 67.66 ms | Matched all ground-truth expectations. |
| PASSED | `jv001_read_unshared_positive` | JV001: Potentially unsafe Java deserialization via readUnshared() | 1 | 1 | 3.35 ms | Matched all ground-truth expectations. |
| PASSED | `jv002_runtime_exec_concat_positive` | JV002: Shell command injection via Runtime.getRuntime().exec() concatenation | 1 | 1 | 4.93 ms | Matched all ground-truth expectations. |
| PASSED | `jv002_runtime_exec_variable_positive` | JV002: Shell command injection via Runtime.exec() variable argument | 1 | 1 | 3.89 ms | Matched all ground-truth expectations. |
| PASSED | `jv002_process_builder_concat_positive` | JV002: Command injection via ProcessBuilder dynamic argument | 1 | 1 | 3.99 ms | Matched all ground-truth expectations. |
| PASSED | `jv003_statement_execute_query_concat_positive` | JV003: SQL injection via Statement.executeQuery() concatenation | 1 | 1 | 2.58 ms | Matched all ground-truth expectations. |
| PASSED | `jv003_connection_prepare_statement_concat_positive` | JV003: SQL injection via Connection.prepareStatement() concatenation | 1 | 1 | 4.54 ms | Matched all ground-truth expectations. |
| PASSED | `jv003_statement_execute_update_concat_positive` | JV003: SQL injection via Statement.executeUpdate() concatenation | 1 | 1 | 4.64 ms | Matched all ground-truth expectations. |
| PASSED | `jv004_new_file_concat_positive` | JV004: Path traversal via new File() dynamic string concatenation | 1 | 1 | 5.22 ms | Matched all ground-truth expectations. |
| PASSED | `jv004_paths_get_dynamic_positive` | JV004: Path traversal via Paths.get() dynamic parameters | 1 | 1 | 3.9 ms | Matched all ground-truth expectations. |
| PASSED | `clean_java_buffered_reader_negative` | Clean: Safe stream processing using BufferedReader | 0 | 0 | 3.23 ms | Matched all ground-truth expectations. |
| PASSED | `clean_java_runtime_exec_constant_negative` | Clean: Safe constant command in Runtime.exec() | 0 | 0 | 2.43 ms | Matched all ground-truth expectations. |
| PASSED | `clean_java_process_builder_constant_negative` | Clean: Safe ProcessBuilder invocation with constant array arguments | 0 | 0 | 1.86 ms | Matched all ground-truth expectations. |
| PASSED | `clean_java_parameterized_sql_negative` | Clean: Parameterized SQL query with PreparedStatement bind placeholders | 0 | 0 | 2.62 ms | Matched all ground-truth expectations. |
| PASSED | `clean_java_constant_file_path_negative` | Clean: Safe constant filesystem path creation | 0 | 0 | 2.94 ms | Matched all ground-truth expectations. |
| PASSED | `edge_java_empty_diff` | Edge: Empty diff patch | 0 | 0 | 1.87 ms | Matched all ground-truth expectations. |
| PASSED | `edge_java_binary_file_diff` | Edge: Binary .class file diff | 0 | 0 | 1.87 ms | Matched all ground-truth expectations. |
| PASSED | `edge_java_non_java_markdown` | Edge: Non-Java markdown documentation diff | 0 | 0 | 2.15 ms | Matched all ground-truth expectations. |
| PASSED | `edge_java_syntax_error` | Edge: Java code with intentional syntax error | 0 | 0 | 1.7 ms | Matched all ground-truth expectations. |
| PASSED | `edge_java_renamed_file_no_changes` | Edge: Renamed file with zero modified lines | 0 | 0 | 1.33 ms | Matched all ground-truth expectations. |

## 6. Evaluation Methodology & Known Limitations

1. **Curated Benchmark Scope:** This evaluation measures performance against versioned synthetic and curated code-diff fixtures. It validates parser correctness, AST matching, and grounding validation, but does not prove real-world bug-detection accuracy across arbitrary unseen repositories.
2. **Evaluation Units:** Precision, Recall, and F1 are evaluated at the Finding level. False Positive Rate (FPR) and True Negatives (TN) are evaluated at the Case level on ground-truth negative fixtures.
3. **Zero Denominator Handling:** When metric denominators evaluate to zero, measurements are reported explicitly as `N/A` rather than manufactured numbers.
4. **Truth-in-Advertising:** Measurements in this report reflect actual code execution without simulated or hardcoded results.