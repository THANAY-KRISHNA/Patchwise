"""Unit and integration tests for the C/C++ benchmark dataset and runner."""
import pytest
from src.benchmark.dataset_cpp import (
    DATASET_NAME_CPP,
    DATASET_VERSION_CPP,
    get_cpp_benchmark_dataset,
)
from src.benchmark.runner import BenchmarkRunner
from src.parser.diff_parser import parse_single_file_patch
from src.schemas.findings import FindingProvenance


def test_cpp_dataset_metadata():
    ds = get_cpp_benchmark_dataset()
    assert ds.name == DATASET_NAME_CPP
    assert ds.version == DATASET_VERSION_CPP
    assert len(ds.cases) == 20


def test_cpp_dataset_case_ids_unique():
    ds = get_cpp_benchmark_dataset()
    case_ids = [c.id for c in ds.cases]
    assert len(case_ids) == len(set(case_ids)), "All case IDs must be unique"


def test_cpp_dataset_distribution_and_provenance():
    ds = get_cpp_benchmark_dataset()
    positives = [c for c in ds.cases if c.expected_findings]
    negatives = [c for c in ds.cases if not c.expected_findings]

    assert len(positives) == 10
    assert len(negatives) == 10

    # Every expected finding must use DETERMINISTIC_STATIC_ANALYSIS tier
    for c in positives:
        for ef in c.expected_findings:
            assert ef.expected_source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
            assert ef.rule_id in ("CC001", "CC002", "CC003", "CC004")

    # Every negative case must have is_negative_case=True
    for c in negatives:
        assert c.is_negative_case is True


def test_cpp_dataset_diff_hunks_parse_cleanly():
    ds = get_cpp_benchmark_dataset()
    for c in ds.cases:
        if c.diff_patch and "binary" not in c.tags:
            parsed = parse_single_file_patch(c.diff_patch, c.target_file)
            assert parsed.file_path == c.target_file


@pytest.mark.asyncio
async def test_cpp_benchmark_runner_offline_execution():
    ds = get_cpp_benchmark_dataset()
    runner = BenchmarkRunner(dataset=ds, provider_id="none")
    summary = await runner.run()

    assert summary.metrics.total_cases == 20
    assert summary.metrics.passed_cases == 20
    assert summary.metrics.failed_cases == 0

    assert summary.metrics.tp == 10
    assert summary.metrics.fp == 0
    assert summary.metrics.fn == 0
    assert summary.metrics.tn == 10

    assert summary.metrics.precision == 1.0
    assert summary.metrics.recall == 1.0
    assert summary.metrics.f1 == 1.0
    assert summary.metrics.false_positive_rate == 0.0
