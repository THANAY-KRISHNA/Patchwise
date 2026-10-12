# Patchwise Benchmark Evaluation Report

## 1. Run Metadata

- **Dataset:** `patchwise-python-deterministic-benchmark` (`v1.0.0`)
- **Engine Version:** `0.1.0`
- **Active Provider:** `none`
- **Run Timestamp (UTC):** `2026-10-12 18:50:45 UTC`
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

- **Mean Latency per Fixture:** `2.64 ms`
- **Median Latency:** `2.13 ms`
- **95th Percentile (p95):** `2.82 ms`
- **Total Benchmark Wall Time:** `52.7 ms`

## 4. Per-Rule Breakdown

| Rule ID | Category / Target | TP | FP | FN | Precision | Recall | F1 Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **PY001** | Missing input validation | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **PY002** | Suspicious exception handling | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **PY003** | Mutable default arguments | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **PY004** | Unsafe eval / pickle / SQL injection | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **PY005** | Missing test heuristic | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

## 5. Case-by-Case Execution Outcomes

| Status | Case ID | Name | Expected | Actual | Latency | Outcome Details |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| PASSED | `py001_missing_validation_positive` | PY001: Unchecked external payload dictionary key access | 1 | 1 | 13.17 ms | Matched all ground-truth expectations. |
| PASSED | `py002_bare_except_positive` | PY002: Bare except clause | 1 | 1 | 2.82 ms | Matched all ground-truth expectations. |
| PASSED | `py002_base_exception_positive` | PY002: Catching BaseException explicitly | 1 | 1 | 2.38 ms | Matched all ground-truth expectations. |
| PASSED | `py002_silent_pass_positive` | PY002: Silent exception suppression with pass | 1 | 1 | 2.2 ms | Matched all ground-truth expectations. |
| PASSED | `py003_mutable_list_default_positive` | PY003: Mutable list default parameter | 1 | 1 | 2.33 ms | Matched all ground-truth expectations. |
| PASSED | `py003_mutable_dict_default_positive` | PY003: Mutable dictionary default parameter | 1 | 1 | 2.37 ms | Matched all ground-truth expectations. |
| PASSED | `py004_eval_positive` | PY004: Insecure dynamic execution with eval() | 1 | 1 | 2.75 ms | Matched all ground-truth expectations. |
| PASSED | `py004_pickle_positive` | PY004: Insecure deserialization via pickle.loads() | 1 | 1 | 2.23 ms | Matched all ground-truth expectations. |
| PASSED | `py004_sql_injection_positive` | PY004: SQL injection via f-string query formatting | 1 | 1 | 2.18 ms | Matched all ground-truth expectations. |
| PASSED | `py005_missing_tests_heuristic_positive` | PY005: Missing unit test recommendation | 1 | 1 | 2.43 ms | Matched all ground-truth expectations. |
| PASSED | `clean_safe_dict_get_negative` | Clean: Safe dictionary access via .get() | 0 | 0 | 1.96 ms | Matched all ground-truth expectations. |
| PASSED | `clean_specific_exception_negative` | Clean: Catching specific exceptions and logging | 0 | 0 | 1.88 ms | Matched all ground-truth expectations. |
| PASSED | `clean_immutable_default_negative` | Clean: Safe None default with body initialization | 0 | 0 | 1.73 ms | Matched all ground-truth expectations. |
| PASSED | `clean_parameterized_sql_negative` | Clean: Parameterized SQL statement with driver bindings | 0 | 0 | 1.66 ms | Matched all ground-truth expectations. |
| PASSED | `clean_business_logic_with_tests_negative` | Clean: Business logic modification accompanied by unit tests | 0 | 0 | 1.89 ms | Matched all ground-truth expectations. |
| PASSED | `edge_empty_diff` | Edge: Empty diff patch | 0 | 0 | 1.82 ms | Matched all ground-truth expectations. |
| PASSED | `edge_binary_file_diff` | Edge: Binary file diff | 0 | 0 | 2.09 ms | Matched all ground-truth expectations. |
| PASSED | `edge_non_python_markdown` | Edge: Non-Python markdown documentation | 0 | 0 | 1.64 ms | Matched all ground-truth expectations. |
| PASSED | `edge_python_syntax_error` | Edge: Python code with syntax error | 0 | 0 | 1.82 ms | Matched all ground-truth expectations. |
| PASSED | `edge_renamed_file_no_changes` | Edge: Renamed file with zero modified lines | 0 | 0 | 1.35 ms | Matched all ground-truth expectations. |

## 6. Evaluation Methodology & Known Limitations

1. **Curated Benchmark Scope:** This evaluation measures performance against versioned synthetic and curated code-diff fixtures. It validates parser correctness, AST matching, and grounding validation, but does not prove real-world bug-detection accuracy across arbitrary unseen repositories.
2. **Evaluation Units:** Precision, Recall, and F1 are evaluated at the Finding level. False Positive Rate (FPR) and True Negatives (TN) are evaluated at the Case level on ground-truth negative fixtures.
3. **Zero Denominator Handling:** When metric denominators evaluate to zero, measurements are reported explicitly as `N/A` rather than manufactured numbers.
4. **Truth-in-Advertising:** Measurements in this report reflect actual code execution without simulated or hardcoded results.