"""Patchwise Benchmark and Evaluation Framework."""
from .dataset import get_default_benchmark_dataset, load_benchmark_dataset
from .metrics import (
    calculate_f1,
    calculate_false_positive_rate,
    calculate_latency_statistics,
    calculate_precision,
    calculate_recall,
)
from .models import (
    AggregateMetrics,
    BenchmarkCase,
    BenchmarkDataset,
    BenchmarkRunSummary,
    CaseOutcome,
    ExpectedFinding,
    RuleMetrics,
)
from .reporter import format_json_report, format_markdown_report
from .runner import BenchmarkRunner

__all__ = [
    "BenchmarkCase",
    "ExpectedFinding",
    "BenchmarkDataset",
    "CaseOutcome",
    "RuleMetrics",
    "AggregateMetrics",
    "BenchmarkRunSummary",
    "calculate_precision",
    "calculate_recall",
    "calculate_f1",
    "calculate_false_positive_rate",
    "calculate_latency_statistics",
    "get_default_benchmark_dataset",
    "load_benchmark_dataset",
    "format_markdown_report",
    "format_json_report",
    "BenchmarkRunner",
]
