"""Tests for Patchwise Benchmark Evaluation Suite (Milestone 5).

Covers:
- Metric calculations (Precision, Recall, F1, FPR, Latency statistics) with zero-denominator handling.
- Finding matching criteria and grounding validation.
- Dataset loading, validation, and versioning.
- Deterministic offline benchmark runner execution and reproducibility.
- JSON and Markdown report formatting and limitation disclosures.
"""
import json
import pytest
from datetime import datetime, timezone

from src.benchmark.dataset import (
    DATASET_NAME,
    DATASET_VERSION,
    get_default_benchmark_dataset,
    load_benchmark_dataset,
)
from src.benchmark.metrics import (
    calculate_f1,
    calculate_false_positive_rate,
    calculate_latency_statistics,
    calculate_precision,
    calculate_recall,
)
from src.benchmark.models import (
    AggregateMetrics,
    BenchmarkCase,
    BenchmarkDataset,
    BenchmarkRunSummary,
    CaseOutcome,
    ExpectedFinding,
    RuleMetrics,
)
from src.benchmark.reporter import format_json_report, format_markdown_report
from src.benchmark.runner import BenchmarkRunner
from src.schemas.findings import (
    FindingCategory,
    FindingCreate,
    FindingProvenance,
    FindingSeverity,
)


# -------------------------------------------------------------------------
# 1. Metric Calculation Tests
# -------------------------------------------------------------------------


class TestMetricCalculations:
    """Tests precision, recall, F1, FPR, and latency stats with zero-denominator handling."""

    def test_precision_standard(self):
        assert calculate_precision(10, 0) == 1.0
        assert calculate_precision(8, 2) == 0.8
        assert calculate_precision(0, 5) == 0.0

    def test_precision_zero_denominator(self):
        """Zero denominator must return None, not 0.0 or divide-by-zero error."""
        assert calculate_precision(0, 0) is None

    def test_recall_standard(self):
        assert calculate_recall(10, 0) == 1.0
        assert calculate_recall(7, 3) == 0.7
        assert calculate_recall(0, 4) == 0.0

    def test_recall_zero_denominator(self):
        """Zero denominator must return None."""
        assert calculate_recall(0, 0) is None

    def test_f1_standard(self):
        assert calculate_f1(1.0, 1.0) == 1.0
        assert calculate_f1(0.8, 0.8) == 0.8
        # precision=0.8, recall=0.6 -> 2 * 0.48 / 1.4 = 0.6857
        assert calculate_f1(0.8, 0.6) == 0.6857

    def test_f1_zero_or_none(self):
        assert calculate_f1(None, 0.8) is None
        assert calculate_f1(0.8, None) is None
        assert calculate_f1(None, None) is None
        assert calculate_f1(0.0, 0.0) is None

    def test_false_positive_rate_standard(self):
        assert calculate_false_positive_rate(0, 10) == 0.0
        assert calculate_false_positive_rate(2, 8) == 0.2
        assert calculate_false_positive_rate(10, 0) == 1.0

    def test_false_positive_rate_zero_denominator(self):
        assert calculate_false_positive_rate(0, 0) is None

    def test_latency_statistics_empty(self):
        stats = calculate_latency_statistics([])
        assert stats["total_ms"] == 0.0
        assert stats["mean_ms"] == 0.0
        assert stats["median_ms"] == 0.0
        assert stats["p95_ms"] == 0.0

    def test_latency_statistics_odd_length(self):
        lats = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = calculate_latency_statistics(lats)
        assert stats["total_ms"] == 150.0
        assert stats["mean_ms"] == 30.0
        assert stats["median_ms"] == 30.0
        assert stats["p95_ms"] == 50.0

    def test_latency_statistics_even_length(self):
        lats = [10.0, 20.0, 30.0, 40.0]
        stats = calculate_latency_statistics(lats)
        assert stats["total_ms"] == 100.0
        assert stats["mean_ms"] == 25.0
        assert stats["median_ms"] == 25.0  # (20 + 30) / 2
        assert stats["p95_ms"] == 40.0


# -------------------------------------------------------------------------
# 2. Finding Matching Criteria Tests
# -------------------------------------------------------------------------


class TestFindingMatchingCriteria:
    """Tests stable matching logic between actual findings and ground-truth expectations."""

    def test_exact_match(self):
        runner = BenchmarkRunner()
        actual = FindingCreate(
            rule_id="PY001",
            category=FindingCategory.INPUT_VALIDATION,
            severity=FindingSeverity.HIGH,
            title="Missing validation",
            explanation="Input unvalidated before operation",
            file_path="app/views.py",
            start_line=15,
            end_line=15,
            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        )
        expected = ExpectedFinding(
            rule_id="PY001",
            file_path="app/views.py",
            start_line=15,
            end_line=15,
            rationale="Expected input validation finding",
        )
        assert runner._matches_expected(actual, expected) is True

    def test_rule_mismatch(self):
        runner = BenchmarkRunner()
        actual = FindingCreate(
            rule_id="PY002",
            category=FindingCategory.EXCEPTION_HANDLING,
            severity=FindingSeverity.MEDIUM,
            title="Bare except",
            explanation="Bare except clause detected",
            file_path="app/views.py",
            start_line=15,
            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        )
        expected = ExpectedFinding(
            rule_id="PY001",
            file_path="app/views.py",
            start_line=15,
            rationale="Expected PY001",
        )
        assert runner._matches_expected(actual, expected) is False

    def test_file_path_mismatch(self):
        runner = BenchmarkRunner()
        actual = FindingCreate(
            rule_id="PY001",
            category=FindingCategory.INPUT_VALIDATION,
            severity=FindingSeverity.HIGH,
            title="Missing validation",
            explanation="Input unvalidated",
            file_path="app/other.py",
            start_line=15,
            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        )
        expected = ExpectedFinding(
            rule_id="PY001",
            file_path="app/views.py",
            start_line=15,
            rationale="Expected in app/views.py",
        )
        assert runner._matches_expected(actual, expected) is False

    def test_line_range_overlap(self):
        runner = BenchmarkRunner()
        actual = FindingCreate(
            rule_id="PY004",
            category=FindingCategory.SECURITY_PATTERN,
            severity=FindingSeverity.CRITICAL,
            title="SQL injection",
            explanation="Unsafe format used in raw SQL",
            file_path="db.py",
            start_line=20,
            end_line=25,
            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        )
        # Expected specifies line 22 (inside 20..25)
        expected = ExpectedFinding(
            rule_id="PY004",
            file_path="db.py",
            start_line=22,
            end_line=22,
            rationale="Line 22 SQL format call",
        )
        assert runner._matches_expected(actual, expected) is True

    def test_line_range_no_overlap(self):
        runner = BenchmarkRunner()
        actual = FindingCreate(
            rule_id="PY004",
            category=FindingCategory.SECURITY_PATTERN,
            severity=FindingSeverity.CRITICAL,
            title="SQL injection",
            explanation="Unsafe format used in raw SQL",
            file_path="db.py",
            start_line=10,
            end_line=12,
            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        )
        expected = ExpectedFinding(
            rule_id="PY004",
            file_path="db.py",
            start_line=22,
            end_line=22,
            rationale="Line 22 SQL format call",
        )
        assert runner._matches_expected(actual, expected) is False

    def test_file_level_expected_matches_any_line(self):
        runner = BenchmarkRunner()
        actual = FindingCreate(
            rule_id="PY005",
            category=FindingCategory.TEST_SUGGESTION,
            severity=FindingSeverity.LOW,
            title="Missing test heuristic",
            explanation="No tests found for modified business logic",
            file_path="app/service.py",
            start_line=10,
            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        )
        expected = ExpectedFinding(
            rule_id="PY005",
            file_path="app/service.py",
            start_line=None,
            end_line=None,
            rationale="File-level PY005 expectation",
        )
        assert runner._matches_expected(actual, expected) is True


# -------------------------------------------------------------------------
# 3. Dataset Loading and Schema Tests
# -------------------------------------------------------------------------


class TestDatasetLoading:
    """Tests benchmark dataset structure and version loading."""

    def test_load_default_dataset(self):
        dataset = get_default_benchmark_dataset()
        assert dataset.name == DATASET_NAME
        assert dataset.version == DATASET_VERSION
        assert len(dataset.cases) == 20

    def test_load_by_version(self):
        dataset = load_benchmark_dataset("v1.0.0")
        assert dataset.version == "v1.0.0"
        assert len(dataset.cases) == 20

    def test_load_unknown_version_raises(self):
        with pytest.raises(ValueError, match="Unknown benchmark dataset version"):
            load_benchmark_dataset("v99.99.99")

    def test_dataset_fixture_integrity(self):
        dataset = get_default_benchmark_dataset()
        case_ids = set()
        for case in dataset.cases:
            # IDs must be unique
            assert case.id not in case_ids, f"Duplicate case id: {case.id}"
            case_ids.add(case.id)

            # Metadata must be populated
            assert len(case.name) > 0
            assert len(case.description) > 0
            assert len(case.target_file) > 0

            # Target file must be in all_pr_files
            assert case.target_file in case.all_pr_files

            # Negative cases must have 0 expected findings
            if case.is_negative_case:
                assert len(case.expected_findings) == 0

            # Positive cases must have >= 1 expected finding with description rationale
            else:
                assert len(case.expected_findings) >= 1
                for exp in case.expected_findings:
                    assert exp.rule_id in {"PY001", "PY002", "PY003", "PY004", "PY005"}
                    assert exp.description is not None and len(exp.description) > 0


# -------------------------------------------------------------------------
# 4. Benchmark Runner Execution and Reproducibility
# -------------------------------------------------------------------------


class TestBenchmarkRunner:
    """Tests end-to-end evaluation runner with orchestrator in offline mode."""

    @pytest.mark.asyncio
    async def test_deterministic_runner_execution(self):
        """Runs the frozen benchmark dataset with LLM_PROVIDER=none in offline mode."""
        runner = BenchmarkRunner(provider_id="none")
        summary = await runner.run()

        # Check metadata
        assert summary.dataset_name == DATASET_NAME
        assert summary.dataset_version == DATASET_VERSION
        assert summary.provider == "none"

        m = summary.metrics
        assert m.total_cases == 20
        assert m.passed_cases == 20
        assert m.failed_cases == 0

        # Ground truth counts: 10 positive findings across 10 positive fixtures
        assert m.tp == 10
        assert m.fp == 0
        assert m.fn == 0
        # 10 negative/edge-case fixtures producing 0 findings = 10 True Negatives
        assert m.tn == 10

        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.f1 == 1.0
        assert m.false_positive_rate == 0.0

        # Latency must be non-zero and recorded
        assert m.total_latency_ms > 0
        assert m.mean_latency_ms > 0
        assert m.median_latency_ms > 0
        assert m.p95_latency_ms > 0

        # Check per-rule stats (PY001: 1, PY002: 3, PY003: 2, PY004: 3, PY005: 1)
        expected_tps = {
            "PY001": 1,
            "PY002": 3,
            "PY003": 2,
            "PY004": 3,
            "PY005": 1,
        }
        for rule_id, expected_tp in expected_tps.items():
            assert rule_id in m.per_rule
            rm = m.per_rule[rule_id]
            assert rm.tp == expected_tp
            assert rm.fp == 0
            assert rm.fn == 0
            assert rm.precision == 1.0
            assert rm.recall == 1.0
            assert rm.f1 == 1.0

    @pytest.mark.asyncio
    async def test_reproducibility(self):
        """Executing twice in succession must produce identical counts and metrics."""
        runner1 = BenchmarkRunner(provider_id="none")
        summary1 = await runner1.run()

        runner2 = BenchmarkRunner(provider_id="none")
        summary2 = await runner2.run()

        assert summary1.metrics.tp == summary2.metrics.tp
        assert summary1.metrics.fp == summary2.metrics.fp
        assert summary1.metrics.fn == summary2.metrics.fn
        assert summary1.metrics.tn == summary2.metrics.tn
        assert summary1.metrics.precision == summary2.metrics.precision
        assert summary1.metrics.recall == summary2.metrics.recall
        assert summary1.metrics.f1 == summary2.metrics.f1
        assert summary1.metrics.false_positive_rate == summary2.metrics.false_positive_rate


# -------------------------------------------------------------------------
# 5. Reporting and Formatting Tests
# -------------------------------------------------------------------------


class TestReportFormatting:
    """Tests JSON and Markdown report generation."""

    @pytest.fixture
    def sample_summary(self):
        per_rule = {
            "PY001": RuleMetrics(
                rule_id="PY001", tp=2, fp=0, fn=0, precision=1.0, recall=1.0, f1=1.0
            ),
            "PY002": RuleMetrics(
                rule_id="PY002", tp=1, fp=1, fn=0, precision=0.5, recall=1.0, f1=0.6667
            ),
        }
        aggregate = AggregateMetrics(
            total_cases=5,
            passed_cases=4,
            failed_cases=1,
            tp=3,
            fp=1,
            fn=0,
            tn=2,
            precision=0.75,
            recall=1.0,
            f1=0.8571,
            false_positive_rate=0.3333,
            total_latency_ms=250.0,
            mean_latency_ms=50.0,
            median_latency_ms=48.0,
            p95_latency_ms=62.0,
            per_rule=per_rule,
        )
        return BenchmarkRunSummary(
            dataset_name="patchwise-core-python-eval",
            dataset_version="v1.0.0",
            engine_version="0.1.0",
            provider="none",
            timestamp=datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc),
            metrics=aggregate,
            case_outcomes=[
                CaseOutcome(
                    case_id="case_1",
                    case_name="Test Case 1",
                    passed=True,
                    tp=2,
                    fp=0,
                    fn=0,
                    tn=0,
                    latency_ms=45.0,
                    expected_count=2,
                    actual_count=2,
                    matched_rules=["PY001", "PY001"],
                    details="Matched all expectations",
                ),
            ],
        )

    def test_json_report_serialization(self, sample_summary):
        json_str = format_json_report(sample_summary)
        data = json.loads(json_str)
        assert data["dataset_name"] == "patchwise-core-python-eval"
        assert data["dataset_version"] == "v1.0.0"
        assert data["provider"] == "none"
        assert data["metrics"]["tp"] == 3
        assert data["metrics"]["precision"] == 0.75
        assert len(data["case_outcomes"]) == 1

    def test_markdown_report_rendering(self, sample_summary):
        md = format_markdown_report(sample_summary)
        # Check required sections
        assert "# Patchwise Benchmark Evaluation Report" in md
        assert "## 1. Run Metadata" in md
        assert "## 2. Overall Performance Metrics" in md
        assert "## 3. Latency Statistics" in md
        assert "## 4. Per-Rule Breakdown" in md
        assert "## 5. Case-by-Case Execution Outcomes" in md
        assert "## 6. Evaluation Methodology & Known Limitations" in md

        # Check values formatted
        assert "75.0%" in md
        assert "100.0%" in md
        assert "50.0 ms" in md
        assert "PY001" in md
        assert "PY002" in md
        assert "case_1" in md
        assert "Curated Benchmark Scope" in md
