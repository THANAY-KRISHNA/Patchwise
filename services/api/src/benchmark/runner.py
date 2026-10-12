"""Benchmark Evaluation Runner for Patchwise.

Executes the analysis orchestrator against versioned benchmark datasets,
computes precision, recall, F1, and latency statistics, and formats structured reports.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..analyzer.orchestrator import AnalysisOrchestrator
from ..core.config import settings
from ..db.base import Base
from ..db.models import EvaluationCase as EvaluationCaseModel, EvaluationRun as EvaluationRunModel
from ..github.mock import MockGitHubClient
from ..github.models import GitHubChangedFile
from ..providers.base import BaseReviewProvider
from ..providers.rule_only import RuleOnlyProvider
from .dataset import DATASET_NAME, DATASET_VERSION, get_default_benchmark_dataset
from .dataset_js import DATASET_NAME_JS, DATASET_VERSION_JS, get_javascript_benchmark_dataset
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

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """
    Orchestrates execution of benchmark test fixtures against Patchwise analyzers.
    Operates in 100% offline mode with zero network calls for deterministic evaluations.
    """

    def __init__(
        self,
        dataset: Optional[BenchmarkDataset] = None,
        provider_id: str = "none",
        llm_provider: Optional[BaseReviewProvider] = None,
        db_session: Optional[AsyncSession] = None,
    ):
        self.dataset = dataset or get_default_benchmark_dataset()
        self.provider_id = provider_id
        self.llm_provider = llm_provider
        self.db_session = db_session

    def _matches_expected(self, actual, expected: ExpectedFinding) -> bool:
        """
        Stable matching criteria:
        1. Rule ID must match (e.g. PY001).
        2. File path must match.
        3. Line numbers: If expected has start_line, actual finding must cover that line.
        """
        if actual.rule_id != expected.rule_id:
            return False
        if actual.file_path != expected.file_path:
            return False
        if expected.start_line is not None:
            if actual.start_line is None:
                return False
            # Check single line or interval overlap
            act_start = actual.start_line
            act_end = actual.end_line or act_start
            exp_start = expected.start_line
            exp_end = expected.end_line or exp_start
            # Lines must overlap
            if act_end < exp_start or act_start > exp_end:
                return False
        return True

    async def _evaluate_single_case(
        self, case: BenchmarkCase, session: AsyncSession
    ) -> CaseOutcome:
        """Executes a single benchmark case diff through the analysis orchestrator."""
        # Build changed files for mock GitHub client
        changed_files: List[GitHubChangedFile] = []

        is_binary = "binary" in case.tags
        target_f = GitHubChangedFile(
            filename=case.target_file,
            status="modified",
            patch=case.diff_patch if (case.diff_patch and not is_binary) else None,
        )
        changed_files.append(target_f)

        for pr_file in case.all_pr_files:
            if pr_file != case.target_file:
                changed_files.append(
                    GitHubChangedFile(
                        filename=pr_file,
                        status="added",
                        patch="@@ -0,0 +1,2 @@\n+test line",
                    )
                )

        mock_gh = MockGitHubClient(sample_files=changed_files)
        rule_provider = RuleOnlyProvider()

        orchestrator = AnalysisOrchestrator(
            db=session,
            github_client=mock_gh,
            rule_provider=rule_provider,
            llm_provider=self.llm_provider if self.provider_id != "none" else None,
        )

        start_time = time.perf_counter()
        review = await orchestrator.run_review(
            repository_url=f"https://github.com/benchmark/{case.id}",
            pull_request_number=1,
        )
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        actual_findings = review.findings or []

        # Stable matching
        expected_matched: Set[int] = set()
        actual_matched: Set[int] = set()

        for exp_idx, expected in enumerate(case.expected_findings):
            for act_idx, actual in enumerate(actual_findings):
                if act_idx in actual_matched:
                    continue
                if self._matches_expected(actual, expected):
                    expected_matched.add(exp_idx)
                    actual_matched.add(act_idx)
                    break

        tp = len(expected_matched)
        fn = len(case.expected_findings) - len(expected_matched)
        fp = len(actual_findings) - len(actual_matched)

        # True Negative and False Positive at case level
        tn = 1 if (case.is_negative_case and len(actual_findings) == 0) else 0
        case_fp = 1 if (case.is_negative_case and len(actual_findings) > 0) else 0

        passed = (fn == 0 and fp == 0)

        matched_rules = [case.expected_findings[i].rule_id for i in expected_matched]
        unmatched_expected = [
            f"{case.expected_findings[i].rule_id}@{case.expected_findings[i].file_path}:{case.expected_findings[i].start_line}"
            for i in range(len(case.expected_findings))
            if i not in expected_matched
        ]
        unexpected_actual = [
            f"{actual_findings[i].rule_id}@{actual_findings[i].file_path}:{actual_findings[i].start_line}"
            for i in range(len(actual_findings))
            if i not in actual_matched
        ]

        details = ""
        if not passed:
            details = f"Missed: {unmatched_expected}; Unexpected: {unexpected_actual}"
        else:
            details = "Matched all ground-truth expectations."

        return CaseOutcome(
            case_id=case.id,
            case_name=case.name,
            passed=passed,
            tp=tp,
            fp=fp,
            fn=fn,
            tn=tn,
            case_fp=case_fp,
            latency_ms=elapsed_ms,
            expected_count=len(case.expected_findings),
            actual_count=len(actual_findings),
            matched_rules=matched_rules,
            unmatched_expected=unmatched_expected,
            unexpected_actual=unexpected_actual,
            details=details,
        )

    async def run(self) -> BenchmarkRunSummary:
        """Execute full benchmark evaluation across all dataset fixtures."""
        # Use provided db_session or build isolated in-memory test session
        should_close_engine = False
        session = self.db_session

        if session is None:
            engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            session = session_factory()
            should_close_engine = True

        outcomes: List[CaseOutcome] = []
        rule_stats: Dict[str, Dict[str, int]] = {}

        try:
            for case in self.dataset.cases:
                outcome = await self._evaluate_single_case(case, session)
                outcomes.append(outcome)

                # Accumulate per-rule stats
                for exp in case.expected_findings:
                    r_id = exp.rule_id
                    if r_id not in rule_stats:
                        rule_stats[r_id] = {"tp": 0, "fp": 0, "fn": 0}
                    if r_id in outcome.matched_rules:
                        rule_stats[r_id]["tp"] += 1
                    else:
                        rule_stats[r_id]["fn"] += 1

                for unexp in outcome.unexpected_actual:
                    r_id = unexp.split("@")[0]
                    if r_id not in rule_stats:
                        rule_stats[r_id] = {"tp": 0, "fp": 0, "fn": 0}
                    rule_stats[r_id]["fp"] += 1

            # Aggregate statistics
            total_cases = len(outcomes)
            passed_cases = sum(1 for o in outcomes if o.passed)
            failed_cases = total_cases - passed_cases

            total_tp = sum(o.tp for o in outcomes)
            total_fp = sum(o.fp for o in outcomes)
            total_fn = sum(o.fn for o in outcomes)
            total_tn = sum(o.tn for o in outcomes)
            total_fp_cases = sum(o.case_fp for o in outcomes)

            precision = calculate_precision(total_tp, total_fp)
            recall = calculate_recall(total_tp, total_fn)
            f1 = calculate_f1(precision, recall)
            fpr = calculate_false_positive_rate(total_fp_cases, total_tn)

            latencies = [o.latency_ms for o in outcomes]
            lat_stats = calculate_latency_statistics(latencies)

            per_rule_metrics: Dict[str, RuleMetrics] = {}
            for r_id, stats in sorted(rule_stats.items()):
                r_prec = calculate_precision(stats["tp"], stats["fp"])
                r_rec = calculate_recall(stats["tp"], stats["fn"])
                r_f1 = calculate_f1(r_prec, r_rec)
                per_rule_metrics[r_id] = RuleMetrics(
                    rule_id=r_id,
                    tp=stats["tp"],
                    fp=stats["fp"],
                    fn=stats["fn"],
                    precision=r_prec,
                    recall=r_rec,
                    f1=r_f1,
                )

            aggregate = AggregateMetrics(
                total_cases=total_cases,
                passed_cases=passed_cases,
                failed_cases=failed_cases,
                tp=total_tp,
                fp=total_fp,
                fn=total_fn,
                tn=total_tn,
                fp_cases=total_fp_cases,
                precision=precision,
                recall=recall,
                f1=f1,
                false_positive_rate=fpr,
                total_latency_ms=lat_stats["total_ms"],
                mean_latency_ms=lat_stats["mean_ms"],
                median_latency_ms=lat_stats["median_ms"],
                p95_latency_ms=lat_stats["p95_ms"],
                per_rule=per_rule_metrics,
            )

            summary = BenchmarkRunSummary(
                dataset_name=self.dataset.name,
                dataset_version=self.dataset.version,
                engine_version=settings.APP_VERSION,
                provider=self.provider_id,
                timestamp=datetime.now(timezone.utc),
                metrics=aggregate,
                case_outcomes=outcomes,
            )

            # Persist to database EvaluationRun table
            eval_run_model = EvaluationRunModel(
                dataset_version=self.dataset.version,
                engine_version=settings.APP_VERSION,
                provider_version=self.provider_id,
                tp=total_tp,
                fp=total_fp,
                fn=total_fn,
                precision=precision,
                recall=recall,
                latency_ms=lat_stats["mean_ms"],
            )
            session.add(eval_run_model)
            await session.commit()

            return summary

        finally:
            if should_close_engine:
                await session.close()
                await engine.dispose()


async def run_benchmark_cli():
    """CLI entry point for running evaluation benchmarks."""
    parser = argparse.ArgumentParser(description="Patchwise Benchmark Evaluation Suite Runner")
    parser.add_argument(
        "--dataset",
        default="python",
        choices=["python", "javascript"],
        help="Benchmark dataset to evaluate: python (default) or javascript",
    )
    parser.add_argument(
        "--provider",
        default="none",
        choices=["none", "mock", "openai", "gemini", "anthropic", "ollama"],
        help="Review provider under test (default: none / deterministic rule-only)",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Path to export evaluation results JSON",
    )
    parser.add_argument(
        "--output-markdown",
        default=None,
        help="Path to export evaluation results Markdown report",
    )
    args = parser.parse_args()

    if args.dataset == "javascript":
        bench_dataset = get_javascript_benchmark_dataset()
    else:
        bench_dataset = get_default_benchmark_dataset()

    print(f"Starting Patchwise Benchmark Runner (Provider: {args.provider}, Dataset: {bench_dataset.name} {bench_dataset.version})...")
    runner = BenchmarkRunner(dataset=bench_dataset, provider_id=args.provider)
    summary = await runner.run()

    md_report = format_markdown_report(summary)
    print("\n" + md_report + "\n")

    if args.output_json:
        json_report = format_json_report(summary)
        with open(args.output_json, "w", encoding="utf-8") as f:
            f.write(json_report)
        print(f"Exported JSON report to {args.output_json}")

    if args.output_markdown:
        with open(args.output_markdown, "w", encoding="utf-8") as f:
            f.write(md_report)
        print(f"Exported Markdown report to {args.output_markdown}")


if __name__ == "__main__":
    asyncio.run(run_benchmark_cli())
