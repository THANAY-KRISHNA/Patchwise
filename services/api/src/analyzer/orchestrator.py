"""Review Pipeline Orchestrator coordinating diff ingestion, analysis, and persistence."""
from datetime import datetime, timezone
import hashlib
import time
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models import Finding, Review
from ..github.client import GitHubClient, parse_github_repo_and_number
from ..parser.diff_parser import parse_single_file_patch
from ..parser.models import ParsedDiffResult, ParsedFileDiff
from ..providers.base import BaseReviewProvider, ReviewContext
from ..providers.rule_only import RuleOnlyProvider
from ..schemas.findings import FindingProvenance, FindingRead
from ..schemas.reviews import ReviewRead, ReviewStatus, ReviewSummary


class AnalysisOrchestrator:
    """
    Composite Pull Request Review Orchestrator:
    1. Parse URL & fetch PR diff metadata.
    2. Parse unified diffs into exact line maps.
    3. Run RuleOnlyProvider for Tier 1 deterministic static analysis findings.
    4. Conditionally run LLMReviewProvider for Tier 2 AI-generated hypotheses.
    5. Handle AI provider failures (timeouts, rate limits, errors) gracefully via fallback.
    6. Deduplicate findings while strictly preserving provenance.
    7. Persist review session and findings to database.
    """

    def __init__(
        self,
        db: AsyncSession,
        github_client: Optional[GitHubClient] = None,
        rule_provider: Optional[RuleOnlyProvider] = None,
        llm_provider: Optional[BaseReviewProvider] = None,
    ):
        self.db = db
        self.github_client = github_client or GitHubClient()
        self.rule_provider = rule_provider or RuleOnlyProvider()

        # Conditionally configure AI review provider
        if llm_provider is not None:
            self.llm_provider = llm_provider
        elif settings.LLM_PROVIDER != "none":
            from ..providers.llm import get_llm_provider
            self.llm_provider = get_llm_provider(settings.LLM_PROVIDER)
        else:
            self.llm_provider = None

    async def run_review(self, repository_url: str, pull_request_number: int) -> ReviewRead:
        owner, repo, pr_number = parse_github_repo_and_number(repository_url, pull_request_number)
        repo_full_name = f"{owner}/{repo}"

        started_at = datetime.now(timezone.utc)
        review_id = uuid.uuid4()

        # Create initial Review record
        review_model = Review(
            id=review_id,
            repository=repo_full_name,
            pr_number=pr_number,
            status=ReviewStatus.FETCHING.value,
            engine_version=settings.APP_VERSION,
            started_at=started_at,
        )
        self.db.add(review_model)
        await self.db.flush()

        # Step 1: Fetch metadata and changed files
        pr_metadata = await self.github_client.get_pull_request(owner, repo, pr_number)
        changed_files = await self.github_client.get_pull_request_files(owner, repo, pr_number)

        review_model.pr_title = pr_metadata.title
        review_model.commit_sha = pr_metadata.head_commit_sha
        review_model.status = ReviewStatus.ANALYZING.value
        await self.db.flush()

        # Step 2: Parse diffs into line mappings
        parsed_files: List[ParsedFileDiff] = []
        total_chars = 0
        for f in changed_files:
            parsed_f = parse_single_file_patch(
                patch_text=f.patch,
                filename=f.filename,
                status=f.status,
                previous_filename=f.previous_filename,
            )
            parsed_files.append(parsed_f)
            total_chars += parsed_f.patch_chars

        parsed_diff = ParsedDiffResult(
            files=parsed_files,
            total_files=len(parsed_files),
            total_patch_chars=total_chars,
        )

        review_context = ReviewContext(
            repository=repo_full_name,
            pr_number=pr_number,
            pr_metadata=pr_metadata,
            parsed_diff=parsed_diff,
            engine_version=settings.APP_VERSION,
        )

        # Step 3: Run Deterministic Static Analysis (Tier 1)
        rule_result = await self.rule_provider.review(review_context)
        rule_provider_status = "completed"

        # Step 4: Run AI Review Provider (Tier 2) if configured
        ai_provider_name: Optional[str] = None
        ai_provider_status: Optional[str] = None
        ai_error_sanitized: Optional[str] = None
        ai_findings: List[Any] = []

        if self.llm_provider is not None:
            ai_provider_name = getattr(self.llm_provider, "provider_id", "ai_provider")
            try:
                ai_result = await self.llm_provider.review(review_context)
                if ai_result.status == "failed":
                    ai_provider_status = "failed"
                    ai_error_sanitized = ai_result.error_message
                else:
                    ai_provider_status = "completed"
                    ai_findings = ai_result.findings
            except Exception as exc:
                ai_provider_status = "failed"
                from ..core.errors import sanitize_secret_text
                ai_error_sanitized = sanitize_secret_text(str(exc))
        else:
            ai_provider_status = "disabled"

        # Step 5: Composite Combination and Deduplication
        combined_candidates = list(rule_result.findings)
        seen_fingerprints = set()

        # Populate deterministic fingerprints
        for cand in combined_candidates:
            fp_data = f"{cand.rule_id}:{cand.file_path}:{cand.start_line}:{cand.end_line}:{cand.title}"
            fp = hashlib.sha256(fp_data.encode("utf-8")).hexdigest()
            seen_fingerprints.add(fp)

        # Merge AI hypotheses with provenance preservation and deduplication
        for ai_cand in ai_findings:
            # Mandate strict provenance separation
            ai_cand.source = FindingProvenance.AI_GENERATED_HYPOTHESIS

            ai_fp_data = f"{ai_cand.rule_id}:{ai_cand.file_path}:{ai_cand.start_line}:{ai_cand.end_line}:{ai_cand.title}"
            ai_fp = hashlib.sha256(ai_fp_data.encode("utf-8")).hexdigest()

            if ai_fp in seen_fingerprints:
                continue

            # Check if deterministic rule already covers the exact location and category
            is_duplicate_of_rule = any(
                r.file_path == ai_cand.file_path
                and r.start_line == ai_cand.start_line
                and r.end_line == ai_cand.end_line
                and r.category == ai_cand.category
                for r in combined_candidates
            )
            if is_duplicate_of_rule:
                continue

            seen_fingerprints.add(ai_fp)
            combined_candidates.append(ai_cand)

        # Step 6: Persist findings to database
        finding_reads: List[FindingRead] = []
        created_at_now = datetime.now(timezone.utc)

        summary = ReviewSummary(
            rule_provider_status=rule_provider_status,
            ai_provider_status=ai_provider_status,
            ai_provider_name=ai_provider_name,
            ai_error_sanitized=ai_error_sanitized,
        )

        for cand in combined_candidates:
            fp_data = f"{cand.rule_id}:{cand.file_path}:{cand.start_line}:{cand.end_line}:{cand.title}"
            fingerprint = hashlib.sha256(fp_data.encode("utf-8")).hexdigest()

            finding_id = uuid.uuid4()
            finding_model = Finding(
                id=finding_id,
                review_id=review_id,
                rule_id=cand.rule_id,
                source=cand.source.value,
                severity=cand.severity.value,
                category=cand.category.value,
                file_path=cand.file_path,
                start_line=cand.start_line,
                end_line=cand.end_line,
                title=cand.title,
                explanation=cand.explanation,
                suggested_fix=cand.suggested_fix,
                fingerprint=fingerprint,
                created_at=created_at_now,
            )
            self.db.add(finding_model)

            # Update summary metrics
            summary.total_findings += 1
            if cand.severity.value == "critical":
                summary.critical_count += 1
            elif cand.severity.value == "high":
                summary.high_count += 1
            elif cand.severity.value == "medium":
                summary.medium_count += 1
            elif cand.severity.value == "low":
                summary.low_count += 1
            elif cand.severity.value == "info":
                summary.info_count += 1

            if cand.source.value == "DETERMINISTIC_STATIC_ANALYSIS":
                summary.deterministic_count += 1
            elif cand.source.value == "AI_GENERATED_HYPOTHESIS":
                summary.ai_hypothesis_count += 1
            elif cand.source.value == "VERIFIED_TEST_RESULT":
                summary.verified_test_count += 1

            finding_reads.append(
                FindingRead(
                    id=finding_id,
                    review_id=review_id,
                    rule_id=cand.rule_id,
                    source=cand.source,
                    severity=cand.severity,
                    category=cand.category,
                    file_path=cand.file_path,
                    start_line=cand.start_line,
                    end_line=cand.end_line,
                    title=cand.title,
                    explanation=cand.explanation,
                    suggested_fix=cand.suggested_fix,
                    fingerprint=fingerprint,
                    created_at=created_at_now,
                )
            )

        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        review_model.status = ReviewStatus.COMPLETED.value
        review_model.completed_at = completed_at
        review_model.duration_ms = duration_ms
        if ai_provider_status == "failed":
            review_model.error_code = "AI_PROVIDER_DEGRADED"
        else:
            review_model.error_code = None

        await self.db.commit()

        return ReviewRead(
            id=review_id,
            repository=repo_full_name,
            pr_number=pr_number,
            pr_title=pr_metadata.title,
            commit_sha=pr_metadata.head_commit_sha,
            status=ReviewStatus.COMPLETED,
            engine_version=settings.APP_VERSION,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error_code=review_model.error_code,
            summary=summary,
            findings=finding_reads,
        )

