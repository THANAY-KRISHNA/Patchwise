"""Data Models for Patchwise Benchmark Evaluation Suite."""
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from ..schemas.findings import FindingProvenance


class ExpectedFinding(BaseModel):
    """Ground-truth expected finding specification in a benchmark case."""
    rule_id: str = Field(..., description="Target rule ID (e.g. 'PY001', 'PY004')")
    file_path: str = Field(..., description="File path relative to repository root")
    start_line: Optional[int] = Field(None, description="Expected start line in the modified file")
    end_line: Optional[int] = Field(None, description="Expected end line in the modified file")
    expected_source: FindingProvenance = Field(
        default=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
        description="Expected provenance tier (Tier 1 vs Tier 2)",
    )
    description: Optional[str] = Field(None, description="Documented rationale for expectation")


class BenchmarkCase(BaseModel):
    """A single code diff test case with ground-truth expectations."""
    id: str = Field(..., description="Unique case identifier, e.g. 'case_py001_basic'")
    name: str = Field(..., description="Human-readable title for the benchmark fixture")
    description: str = Field(..., description="Detailed description of the bug or edge case pattern")
    language: str = Field(default="python", description="Target programming language")
    diff_patch: str = Field(..., description="Unified Git diff patch string")
    target_file: str = Field(..., description="Primary modified file under test")
    all_pr_files: List[str] = Field(default_factory=list, description="All changed files in the mock PR")
    expected_findings: List[ExpectedFinding] = Field(
        default_factory=list, description="Ground truth findings expected from analysis"
    )
    is_negative_case: bool = Field(
        default=False, description="True if this fixture is clean code expecting zero findings (True Negative)"
    )
    tags: List[str] = Field(default_factory=list, description="Categorization tags, e.g. ['security', 'clean']")


class BenchmarkDataset(BaseModel):
    """Versioned collection of labelled benchmark test fixtures."""
    name: str
    version: str
    description: str
    cases: List[BenchmarkCase] = Field(default_factory=list)


class CaseOutcome(BaseModel):
    """Detailed evaluation result for an individual benchmark case."""
    case_id: str
    case_name: str
    passed: bool
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    latency_ms: float = 0.0
    expected_count: int = 0
    actual_count: int = 0
    matched_rules: List[str] = Field(default_factory=list)
    unmatched_expected: List[str] = Field(default_factory=list)
    unexpected_actual: List[str] = Field(default_factory=list)
    details: str = ""


class RuleMetrics(BaseModel):
    """Evaluation metrics computed for a specific rule ID."""
    rule_id: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None


class AggregateMetrics(BaseModel):
    """Aggregated statistical performance metrics across the benchmark suite."""
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    false_positive_rate: Optional[float] = None
    total_latency_ms: float = 0.0
    mean_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    per_rule: Dict[str, RuleMetrics] = Field(default_factory=dict)


class BenchmarkRunSummary(BaseModel):
    """Complete summary of a benchmark evaluation run."""
    dataset_name: str
    dataset_version: str
    engine_version: str
    provider: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: AggregateMetrics
    case_outcomes: List[CaseOutcome] = Field(default_factory=list)
