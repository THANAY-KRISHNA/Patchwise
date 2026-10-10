"""Review and Diff Ingestion Router for Patchwise."""
from typing import AsyncGenerator, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..analyzer.orchestrator import AnalysisOrchestrator
from ..core.errors import ErrorCode, PatchwiseAPIException
from ..db.models import Feedback, Finding, Review
from ..db.session import get_db
from ..github.client import GitHubClient, parse_github_repo_and_number
from ..parser.diff_parser import parse_single_file_patch
from ..parser.models import ParsedFileDiff
from ..schemas.findings import (
    FeedbackCreate,
    FeedbackRead,
    FindingCategory,
    FindingProvenance,
    FindingRead,
    FindingSeverity,
)
from ..schemas.reviews import ReviewRead, ReviewStatus, ReviewSubmissionRequest, ReviewSummary

router = APIRouter(prefix="/reviews", tags=["Reviews & Diffs"])


class DiffInspectionResponse(BaseModel):
    repository: str
    pr_number: int
    title: str
    base_commit_sha: str
    head_commit_sha: str
    total_files_changed: int
    total_added_lines: int
    total_deleted_lines: int
    files: List[ParsedFileDiff]


def get_github_client() -> GitHubClient:
    return GitHubClient()


@router.post("", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def create_pull_request_review(
    payload: ReviewSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    github_client: GitHubClient = Depends(get_github_client),
):
    """
    Initiate and execute a pull request review.
    Runs deterministic AST rules and persists findings and review history.
    """
    orchestrator = AnalysisOrchestrator(db=db, github_client=github_client)
    return await orchestrator.run_review(
        repository_url=str(payload.repository_url),
        pull_request_number=payload.pull_request_number,
    )


@router.get("", response_model=List[ReviewRead])
async def list_recent_reviews(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Fetch recent review history for dashboard."""
    try:
        query = select(Review).order_by(Review.started_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        reviews = result.scalars().all()

        review_reads = []
        for r in reviews:
            findings_query = select(Finding).where(Finding.review_id == r.id)
            f_res = await db.execute(findings_query)
            findings = f_res.scalars().all()

            summary = ReviewSummary(total_findings=len(findings))
            for f in findings:
                if f.severity == "critical":
                    summary.critical_count += 1
                elif f.severity == "high":
                    summary.high_count += 1
                elif f.severity == "medium":
                    summary.medium_count += 1
                elif f.severity == "low":
                    summary.low_count += 1
                elif f.severity == "info":
                    summary.info_count += 1

                if f.source == "DETERMINISTIC_STATIC_ANALYSIS":
                    summary.deterministic_count += 1
                elif f.source == "AI_GENERATED_HYPOTHESIS":
                    summary.ai_hypothesis_count += 1
                elif f.source == "VERIFIED_TEST_RESULT":
                    summary.verified_test_count += 1

            review_reads.append(
                ReviewRead(
                    id=r.id,
                    repository=r.repository,
                    pr_number=r.pr_number,
                    pr_title=r.pr_title,
                    commit_sha=r.commit_sha,
                    status=ReviewStatus(r.status),
                    engine_version=r.engine_version,
                    started_at=r.started_at,
                    completed_at=r.completed_at,
                    duration_ms=r.duration_ms,
                    error_code=r.error_code,
                    summary=summary,
                    findings=[FindingRead.model_validate(f) for f in findings],
                )
            )
        return review_reads
    except Exception:
        return []


@router.get("/{review_id}", response_model=ReviewRead)
async def get_review_by_id(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetch review metadata and summary by ID."""
    try:
        query = select(Review).where(Review.id == review_id)
        result = await db.execute(query)
        review = result.scalar_one_or_none()
    except Exception:
        raise PatchwiseAPIException(
            status_code=503,
            error_code=ErrorCode.DATABASE_ERROR,
            message="Database service temporarily unavailable.",
        )

    if not review:
        raise PatchwiseAPIException(
            status_code=404,
            error_code=ErrorCode.PR_NOT_FOUND,
            message=f"Review '{review_id}' not found.",
        )

    # Fetch associated findings
    findings_query = select(Finding).where(Finding.review_id == review_id)
    findings_res = await db.execute(findings_query)
    findings = findings_res.scalars().all()

    summary = ReviewSummary(total_findings=len(findings))
    for f in findings:
        if f.severity == "critical":
            summary.critical_count += 1
        elif f.severity == "high":
            summary.high_count += 1
        elif f.severity == "medium":
            summary.medium_count += 1
        elif f.severity == "low":
            summary.low_count += 1
        elif f.severity == "info":
            summary.info_count += 1

        if f.source == "DETERMINISTIC_STATIC_ANALYSIS":
            summary.deterministic_count += 1
        elif f.source == "AI_GENERATED_HYPOTHESIS":
            summary.ai_hypothesis_count += 1
        elif f.source == "VERIFIED_TEST_RESULT":
            summary.verified_test_count += 1

    return ReviewRead(
        id=review.id,
        repository=review.repository,
        pr_number=review.pr_number,
        pr_title=review.pr_title,
        commit_sha=review.commit_sha,
        status=ReviewStatus(review.status),
        engine_version=review.engine_version,
        started_at=review.started_at,
        completed_at=review.completed_at,
        duration_ms=review.duration_ms,
        error_code=review.error_code,
        summary=summary,
        findings=[FindingRead.model_validate(f) for f in findings],
    )


@router.get("/{review_id}/findings", response_model=List[FindingRead])
async def get_review_findings(
    review_id: uuid.UUID,
    severity: Optional[FindingSeverity] = Query(None),
    category: Optional[FindingCategory] = Query(None),
    source: Optional[FindingProvenance] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Fetch paginated/filtered findings for a specific review."""
    query = select(Finding).where(Finding.review_id == review_id)

    if severity:
        query = query.where(Finding.severity == severity.value)
    if category:
        query = query.where(Finding.category == category.value)
    if source:
        query = query.where(Finding.source == source.value)

    result = await db.execute(query)
    findings = result.scalars().all()
    return [FindingRead.model_validate(f) for f in findings]


@router.post(
    "/{review_id}/findings/{finding_id}/feedback",
    response_model=FeedbackRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_finding_feedback(
    review_id: uuid.UUID,
    finding_id: uuid.UUID,
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
):
    """Record reviewer feedback (useful, incorrect, irrelevant) on a finding."""
    f_res = await db.execute(
        select(Finding).where(Finding.id == finding_id, Finding.review_id == review_id)
    )
    finding = f_res.scalar_one_or_none()
    if not finding:
        raise PatchwiseAPIException(
            status_code=404,
            error_code=ErrorCode.PR_NOT_FOUND,
            message=f"Finding '{finding_id}' not found for review '{review_id}'.",
        )

    feedback_record = Feedback(
        finding_id=finding_id,
        verdict=payload.verdict.value,
        comment=payload.comment,
    )
    db.add(feedback_record)
    await db.commit()
    await db.refresh(feedback_record)
    return FeedbackRead.model_validate(feedback_record)


@router.post("/inspect", response_model=DiffInspectionResponse, status_code=status.HTTP_200_OK)
async def inspect_pull_request_diff(
    payload: ReviewSubmissionRequest,
    github_client: GitHubClient = Depends(get_github_client),
):
    """
    Fetch and parse pull request diffs without executing analysis rules.
    Verifies GitHub integration and returns exact line mappings.
    """
    owner, repo, pr_number = parse_github_repo_and_number(
        str(payload.repository_url), payload.pull_request_number
    )

    pr_metadata = await github_client.get_pull_request(owner, repo, pr_number)
    changed_files = await github_client.get_pull_request_files(owner, repo, pr_number)

    parsed_files: List[ParsedFileDiff] = []
    total_added = 0
    total_deleted = 0

    for f in changed_files:
        parsed_f = parse_single_file_patch(
            patch_text=f.patch,
            filename=f.filename,
            status=f.status,
            previous_filename=f.previous_filename,
        )
        parsed_files.append(parsed_f)
        total_added += len(parsed_f.added_lines)
        total_deleted += len(parsed_f.deleted_lines)

    return DiffInspectionResponse(
        repository=f"{owner}/{repo}",
        pr_number=pr_number,
        title=pr_metadata.title,
        base_commit_sha=pr_metadata.base_commit_sha,
        head_commit_sha=pr_metadata.head_commit_sha,
        total_files_changed=len(parsed_files),
        total_added_lines=total_added,
        total_deleted_lines=total_deleted,
        files=parsed_files,
    )
