"""Rule-Only Review Provider for 100% Deterministic, Offline Pull Request Analysis."""
import hashlib
import time
from typing import List, Optional
from ..analyzer.base import CandidateFinding
from ..analyzer.registry import LanguagePluginRegistry, plugin_registry
from ..schemas.findings import FindingProvenance
from ..validator.grounding import LineGroundingValidator
from .base import BaseReviewProvider, ReviewContext, ReviewResult


class RuleOnlyProvider(BaseReviewProvider):
    """
    Offline deterministic review provider.
    Executes AST and static analysis rules without requiring LLM credentials, network access, or tokens.
    Enforces DETERMINISTIC_STATIC_ANALYSIS provenance for deterministic rule evaluation.
    """

    def __init__(self, registry: Optional[LanguagePluginRegistry] = None):
        self.registry = registry or plugin_registry

    @property
    def provider_id(self) -> str:
        return "rule_only"

    async def review(self, context: ReviewContext) -> ReviewResult:
        start_time = time.perf_counter()

        validator = LineGroundingValidator(context.parsed_diff)
        all_file_paths = [f.file_path for f in context.parsed_diff.files]

        raw_candidates: List[CandidateFinding] = []

        # 1. Run deterministic checks per changed file
        for file_diff in context.parsed_diff.files:
            analyzer = self.registry.get_analyzer_for_file(file_diff.file_path)
            if not analyzer:
                continue

            findings = analyzer.run_deterministic_checks(
                file_path=file_diff.file_path,
                diff_hunks=file_diff.hunks,
                all_pr_files=all_file_paths,
            )
            raw_candidates.extend(findings)

        # 2. Validate all candidates with LineGroundingValidator
        # Rule findings must strictly Anchor to changed lines
        accepted_candidates: List[CandidateFinding] = []
        seen_fingerprints = set()

        for candidate in raw_candidates:
            # Guarantee strict provenance separation
            if candidate.rule_id == "PY005":
                candidate.source = FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
            else:
                candidate.source = FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS

            val_result = validator.validate_finding(
                candidate,
                require_changed_line=True,
                allow_file_level=(candidate.start_line is None and candidate.end_line is None),
            )

            if val_result.is_valid:
                # Calculate stable SHA-256 fingerprint for deduplication
                fp_data = f"{candidate.rule_id}:{candidate.file_path}:{candidate.start_line}:{candidate.end_line}:{candidate.title}"
                fingerprint = hashlib.sha256(fp_data.encode("utf-8")).hexdigest()

                if fingerprint not in seen_fingerprints:
                    seen_fingerprints.add(fingerprint)
                    accepted_candidates.append(candidate)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return ReviewResult(
            provider_name=self.provider_id,
            findings=accepted_candidates,
            raw_findings_count=len(raw_candidates),
            grounded_findings_count=len(accepted_candidates),
            duration_ms=elapsed_ms,
        )
