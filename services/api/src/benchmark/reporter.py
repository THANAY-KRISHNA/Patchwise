"""Reporting and Export Engine for Patchwise Benchmark Suite."""
import json
from .models import BenchmarkRunSummary


def format_json_report(summary: BenchmarkRunSummary) -> str:
    """Serializes the benchmark evaluation summary to formatted JSON."""
    return summary.model_dump_json(indent=2)


def format_markdown_report(summary: BenchmarkRunSummary) -> str:
    """Renders a readable, comprehensive Markdown report from benchmark run summary."""
    m = summary.metrics

    def fmt_pct(val):
        if val is None:
            return "N/A"
        return f"{round(val * 100, 2)}%"

    def fmt_val(val):
        if val is None:
            return "N/A"
        return f"{val:.4f}"

    pass_rate = round((m.passed_cases / m.total_cases) * 100, 2) if m.total_cases > 0 else 0.0

    lines = [
        "# Patchwise Benchmark Evaluation Report",
        "",
        "## 1. Run Metadata",
        "",
        f"- **Dataset:** `{summary.dataset_name}` (`{summary.dataset_version}`)",
        f"- **Engine Version:** `{summary.engine_version}`",
        f"- **Active Provider:** `{summary.provider}`",
        f"- **Run Timestamp (UTC):** `{summary.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        f"- **Total Fixtures Evaluated:** `{m.total_cases}`",
        "",
        "## 2. Overall Performance Metrics",
        "",
        "| Metric | Measured Value | Unit / Definition |",
        "| :--- | :--- | :--- |",
        f"| **Pass Rate** | **{pass_rate}%** | Passed Fixtures ({m.passed_cases}/{m.total_cases}) |",
        f"| **True Positives (TP)** | {m.tp} | Ground-truth defects correctly detected (Finding level) |",
        f"| **False Positives (FP)** | {m.fp} | Spurious findings on code (Finding level) |",
        f"| **False Negatives (FN)** | {m.fn} | Expected defects missed by analyzer (Finding level) |",
        f"| **True Negatives (TN)** | {m.tn} | Clean/edge fixtures correctly producing 0 findings (Case level) |",
        f"| **Precision** | **{fmt_val(m.precision)}** ({fmt_pct(m.precision)}) | TP / (TP + FP) at finding level |",
        f"| **Recall** | **{fmt_val(m.recall)}** ({fmt_pct(m.recall)}) | TP / (TP + FN) at finding level |",
        f"| **F1 Score** | **{fmt_val(m.f1)}** | Harmonic mean of Precision & Recall (Finding level) |",
        f"| **False Positive Rate** | {fmt_val(m.false_positive_rate)} ({fmt_pct(m.false_positive_rate)}) | FP cases / (FP cases + TN cases) at case level |",
        "",
        "## 3. Latency Statistics",
        "",
        f"- **Mean Latency per Fixture:** `{m.mean_latency_ms} ms`",
        f"- **Median Latency:** `{m.median_latency_ms} ms`",
        f"- **95th Percentile (p95):** `{m.p95_latency_ms} ms`",
        f"- **Total Benchmark Wall Time:** `{m.total_latency_ms} ms`",
        "",
        "## 4. Per-Rule Breakdown",
        "",
        "| Rule ID | Category / Target | TP | FP | FN | Precision | Recall | F1 Score |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    rule_descriptions = {
        "PY001": "Missing input validation",
        "PY002": "Suspicious exception handling",
        "PY003": "Mutable default arguments",
        "PY004": "Unsafe eval / pickle / SQL injection",
        "PY005": "Missing test heuristic",
        "JS001": "Dynamic code execution",
        "JS002": "DOM HTML injection / XSS",
        "JS003": "Shell command injection",
        "JS004": "SQL injection",
        "JV001": "Unsafe deserialization",
        "JV002": "Command injection",
        "JV003": "JDBC SQL injection",
        "JV004": "Path traversal",
        "CC001": "Unbounded string / formatting APIs",
        "CC002": "Format-string misuse",
        "CC003": "Command injection via system/popen",
        "CC004": "Insecure temporary filename APIs",
    }

    for rule_id, rm in m.per_rule.items():
        desc = rule_descriptions.get(rule_id, "Static rule")
        lines.append(
            f"| **{rule_id}** | {desc} | {rm.tp} | {rm.fp} | {rm.fn} | {fmt_val(rm.precision)} | {fmt_val(rm.recall)} | {fmt_val(rm.f1)} |"
        )

    lines.extend([
        "",
        "## 5. Case-by-Case Execution Outcomes",
        "",
        "| Status | Case ID | Name | Expected | Actual | Latency | Outcome Details |",
        "| :---: | :--- | :--- | :---: | :---: | :---: | :--- |",
    ])

    for o in summary.case_outcomes:
        status_badge = "PASSED" if o.passed else "FAILED"
        lines.append(
            f"| {status_badge} | `{o.case_id}` | {o.case_name} | {o.expected_count} | {o.actual_count} | {o.latency_ms} ms | {o.details} |"
        )

    lines.extend([
        "",
        "## 6. Evaluation Methodology & Known Limitations",
        "",
        "1. **Curated Benchmark Scope:** This evaluation measures performance against versioned synthetic and curated code-diff fixtures. It validates parser correctness, AST matching, and grounding validation, but does not prove real-world bug-detection accuracy across arbitrary unseen repositories.",
        "2. **Evaluation Units:** Precision, Recall, and F1 are evaluated at the Finding level. False Positive Rate (FPR) and True Negatives (TN) are evaluated at the Case level on ground-truth negative fixtures.",
        "3. **Zero Denominator Handling:** When metric denominators evaluate to zero, measurements are reported explicitly as `N/A` rather than manufactured numbers.",
        "4. **Truth-in-Advertising:** Measurements in this report reflect actual code execution without simulated or hardcoded results.",
    ])

    return "\n".join(lines)
