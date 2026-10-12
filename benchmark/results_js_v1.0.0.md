# Patchwise Benchmark Evaluation Report

## 1. Run Metadata

- **Dataset:** `patchwise-javascript-deterministic-benchmark` (`v1.0.0`)
- **Engine Version:** `0.1.0`
- **Active Provider:** `none`
- **Run Timestamp (UTC):** `2026-10-12 18:51:01 UTC`
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

- **Mean Latency per Fixture:** `2.78 ms`
- **Median Latency:** `2.24 ms`
- **95th Percentile (p95):** `3.52 ms`
- **Total Benchmark Wall Time:** `55.56 ms`

## 4. Per-Rule Breakdown

| Rule ID | Category / Target | TP | FP | FN | Precision | Recall | F1 Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **JS001** | Static rule | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **JS002** | Static rule | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **JS003** | Static rule | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **JS004** | Static rule | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

## 5. Case-by-Case Execution Outcomes

| Status | Case ID | Name | Expected | Actual | Latency | Outcome Details |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| PASSED | `js001_eval_positive` | JS001: Arbitrary code execution with eval() | 1 | 1 | 13.89 ms | Matched all ground-truth expectations. |
| PASSED | `js001_new_function_positive` | JS001: Dynamic code execution via new Function() | 1 | 1 | 3.52 ms | Matched all ground-truth expectations. |
| PASSED | `js001_set_timeout_string_positive` | JS001: String-based dynamic evaluation in setTimeout() | 1 | 1 | 2.71 ms | Matched all ground-truth expectations. |
| PASSED | `js002_inner_html_positive` | JS002: DOM HTML injection via innerHTML assignment | 1 | 1 | 2.53 ms | Matched all ground-truth expectations. |
| PASSED | `js002_document_write_positive` | JS002: Direct DOM stream injection via document.write() | 1 | 1 | 2.52 ms | Matched all ground-truth expectations. |
| PASSED | `js002_dangerously_set_inner_html_positive` | JS002: Unsanitized React rendering with dangerouslySetInnerHTML | 1 | 1 | 2.73 ms | Matched all ground-truth expectations. |
| PASSED | `js003_exec_template_literal_positive` | JS003: Shell command injection via template literal | 1 | 1 | 2.41 ms | Matched all ground-truth expectations. |
| PASSED | `js003_exec_concat_positive` | JS003: Shell command injection via string concatenation | 1 | 1 | 2.23 ms | Matched all ground-truth expectations. |
| PASSED | `js004_sql_template_positive` | JS004: SQL injection via template literal in db.query() | 1 | 1 | 2.59 ms | Matched all ground-truth expectations. |
| PASSED | `js004_sql_concat_positive` | JS004: SQL injection via string concatenation | 1 | 1 | 2.83 ms | Matched all ground-truth expectations. |
| PASSED | `clean_js_safe_timeout_negative` | Clean: Safe callback function passed to setTimeout | 0 | 0 | 1.99 ms | Matched all ground-truth expectations. |
| PASSED | `clean_js_text_content_negative` | Clean: Safe DOM update using textContent | 0 | 0 | 1.82 ms | Matched all ground-truth expectations. |
| PASSED | `clean_js_exec_file_negative` | Clean: Safe process execution via execFile with argument array | 0 | 0 | 1.73 ms | Matched all ground-truth expectations. |
| PASSED | `clean_js_parameterized_sql_negative` | Clean: Parameterized SQL query with driver bind variables | 0 | 0 | 2.07 ms | Matched all ground-truth expectations. |
| PASSED | `clean_jsx_component_negative` | Clean: Standard React JSX rendering without raw HTML | 0 | 0 | 2.24 ms | Matched all ground-truth expectations. |
| PASSED | `edge_js_empty_diff` | Edge: Empty diff patch | 0 | 0 | 1.55 ms | Matched all ground-truth expectations. |
| PASSED | `edge_js_binary_file_diff` | Edge: Binary file diff | 0 | 0 | 1.48 ms | Matched all ground-truth expectations. |
| PASSED | `edge_js_non_js_markdown` | Edge: Non-JavaScript markdown documentation diff | 0 | 0 | 1.49 ms | Matched all ground-truth expectations. |
| PASSED | `edge_js_syntax_error` | Edge: JavaScript code with intentional syntax error | 0 | 0 | 1.81 ms | Matched all ground-truth expectations. |
| PASSED | `edge_js_renamed_file_no_changes` | Edge: Renamed file with zero modified lines | 0 | 0 | 1.42 ms | Matched all ground-truth expectations. |

## 6. Evaluation Methodology & Known Limitations

1. **Curated Benchmark Scope:** This evaluation measures performance against versioned synthetic and curated code-diff fixtures. It validates parser correctness, AST matching, and grounding validation, but does not prove real-world bug-detection accuracy across arbitrary unseen repositories.
2. **Evaluation Units:** Precision, Recall, and F1 are evaluated at the Finding level. False Positive Rate (FPR) and True Negatives (TN) are evaluated at the Case level on ground-truth negative fixtures.
3. **Zero Denominator Handling:** When metric denominators evaluate to zero, measurements are reported explicitly as `N/A` rather than manufactured numbers.
4. **Truth-in-Advertising:** Measurements in this report reflect actual code execution without simulated or hardcoded results.