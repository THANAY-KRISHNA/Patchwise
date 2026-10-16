# Patchwise Benchmark Evaluation Report

## 1. Run Metadata

- **Dataset:** `patchwise-cpp-deterministic-benchmark` (`v1.0.0`)
- **Engine Version:** `0.1.0`
- **Active Provider:** `none`
- **Run Timestamp (UTC):** `2026-10-13 17:45:47 UTC`
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

- **Mean Latency per Fixture:** `4.18 ms`
- **Median Latency:** `2.12 ms`
- **95th Percentile (p95):** `4.21 ms`
- **Total Benchmark Wall Time:** `83.6 ms`

## 4. Per-Rule Breakdown

| Rule ID | Category / Target | TP | FP | FN | Precision | Recall | F1 Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CC001** | Unbounded string / formatting APIs | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **CC002** | Format-string misuse | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **CC003** | Command injection via system/popen | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **CC004** | Insecure temporary filename APIs | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

## 5. Case-by-Case Execution Outcomes

| Status | Case ID | Name | Expected | Actual | Latency | Outcome Details |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| PASSED | `cc001_gets_positive` | CC001: Unbounded buffer read via gets() | 1 | 1 | 43.56 ms | Matched all ground-truth expectations. |
| PASSED | `cc001_strcpy_positive` | CC001: Unbounded string copy via strcpy() | 1 | 1 | 2.87 ms | Matched all ground-truth expectations. |
| PASSED | `cc001_sprintf_positive` | CC001: Unbounded string formatting via sprintf() | 1 | 1 | 4.21 ms | Matched all ground-truth expectations. |
| PASSED | `cc002_printf_variable_format_positive` | CC002: Format string vulnerability via printf(user_input) | 1 | 1 | 2.4 ms | Matched all ground-truth expectations. |
| PASSED | `cc002_fprintf_variable_format_positive` | CC002: Format string vulnerability via fprintf(stderr, error_msg) | 1 | 1 | 2.53 ms | Matched all ground-truth expectations. |
| PASSED | `cc002_snprintf_variable_format_positive` | CC002: Format string vulnerability via snprintf() non-literal format | 1 | 1 | 2.19 ms | Matched all ground-truth expectations. |
| PASSED | `cc003_system_variable_command_positive` | CC003: Command injection via system() dynamic command | 1 | 1 | 2.15 ms | Matched all ground-truth expectations. |
| PASSED | `cc003_popen_concat_command_positive` | CC003: Command injection via popen() concatenated string | 1 | 1 | 2.61 ms | Matched all ground-truth expectations. |
| PASSED | `cc004_tmpnam_positive` | CC004: Insecure temporary filename generation via tmpnam() | 1 | 1 | 2.5 ms | Matched all ground-truth expectations. |
| PASSED | `cc004_mktemp_positive` | CC004: Insecure temporary filename generation via mktemp() | 1 | 1 | 2.13 ms | Matched all ground-truth expectations. |
| PASSED | `clean_cpp_bounded_string_negative` | Clean: Safe bounded string copying using strncpy and fgets | 0 | 0 | 1.63 ms | Matched all ground-truth expectations. |
| PASSED | `clean_cpp_printf_specifier_negative` | Clean: Safe printf with static format specifier placeholder | 0 | 0 | 1.84 ms | Matched all ground-truth expectations. |
| PASSED | `clean_cpp_printf_fixed_literal_negative` | Clean: Safe fixed string literal in printf() | 0 | 0 | 2.1 ms | Matched all ground-truth expectations. |
| PASSED | `clean_cpp_system_constant_command_negative` | Clean: Safe constant command literal in system() | 0 | 0 | 1.75 ms | Matched all ground-truth expectations. |
| PASSED | `clean_cpp_mkstemp_atomic_temp_negative` | Clean: Safe atomic temporary file creation via mkstemp() | 0 | 0 | 1.72 ms | Matched all ground-truth expectations. |
| PASSED | `edge_cpp_empty_diff` | Edge: Empty diff patch | 0 | 0 | 1.31 ms | Matched all ground-truth expectations. |
| PASSED | `edge_cpp_binary_object_file_diff` | Edge: Binary compiled .o object file diff | 0 | 0 | 1.91 ms | Matched all ground-truth expectations. |
| PASSED | `edge_cpp_non_cpp_markdown` | Edge: Non-C/C++ markdown documentation diff | 0 | 0 | 1.46 ms | Matched all ground-truth expectations. |
| PASSED | `edge_cpp_syntax_error` | Edge: C/C++ code with intentional syntax error | 0 | 0 | 1.54 ms | Matched all ground-truth expectations. |
| PASSED | `edge_cpp_renamed_file_no_changes` | Edge: Renamed header file with zero modified lines | 0 | 0 | 1.19 ms | Matched all ground-truth expectations. |

## 6. Evaluation Methodology & Known Limitations

1. **Curated Benchmark Scope:** This evaluation measures performance against versioned synthetic and curated code-diff fixtures. It validates parser correctness, AST matching, and grounding validation, but does not prove real-world bug-detection accuracy across arbitrary unseen repositories.
2. **Evaluation Units:** Precision, Recall, and F1 are evaluated at the Finding level. False Positive Rate (FPR) and True Negatives (TN) are evaluated at the Case level on ground-truth negative fixtures.
3. **Zero Denominator Handling:** When metric denominators evaluate to zero, measurements are reported explicitly as `N/A` rather than manufactured numbers.
4. **Truth-in-Advertising:** Measurements in this report reflect actual code execution without simulated or hardcoded results.