"""Unit tests for SQLAlchemy database models."""
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Feedback, Finding, PullRequest, Repository, Review, User
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity


@pytest.mark.asyncio
async def test_user_and_repo_creation(db_session: AsyncSession):
    # Create user
    user = User(email="reviewer@example.com", username="test_reviewer")
    db_session.add(user)

    # Create repository
    repo = Repository(owner="owner", name="repo", full_name="owner/repo")
    db_session.add(repo)
    await db_session.commit()

    # Query back
    result = await db_session.execute(select(Repository).where(Repository.full_name == "owner/repo"))
    saved_repo = result.scalar_one()
    assert saved_repo.owner == "owner"
    assert saved_repo.name == "repo"


@pytest.mark.asyncio
async def test_review_and_finding_relationship(db_session: AsyncSession):
    review = Review(
        repository="owner/repo",
        pr_number=42,
        pr_title="Add user validation",
        commit_sha="a" * 40,
        status="completed",
        engine_version="0.1.0",
        duration_ms=450,
    )
    db_session.add(review)
    await db_session.flush()

    finding = Finding(
        review_id=review.id,
        rule_id="PY001",
        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS.value,
        severity=FindingSeverity.HIGH.value,
        category=FindingCategory.INPUT_VALIDATION.value,
        file_path="src/api.py",
        start_line=15,
        end_line=15,
        title="Unvalidated user parameter",
        explanation="Missing validation on query param",
        fingerprint="dummy_hash_12345",
    )
    db_session.add(finding)
    await db_session.flush()

    feedback = Feedback(
        finding_id=finding.id,
        verdict="useful",
        comment="Accurate finding",
    )
    db_session.add(feedback)
    await db_session.commit()

    # Verify query
    res = await db_session.execute(select(Finding).where(Finding.id == finding.id))
    fetched_finding = res.scalar_one()
    assert fetched_finding.rule_id == "PY001"
    assert fetched_finding.source == "DETERMINISTIC_STATIC_ANALYSIS"
    assert fetched_finding.review_id == review.id
