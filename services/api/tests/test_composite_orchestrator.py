"""Integration tests for the Composite Review Orchestrator and Fallback Mechanics."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.analyzer.orchestrator import AnalysisOrchestrator
from src.core.config import settings
from src.core.errors import LLMTimeoutError
from src.github.mock import MockGitHubClient, SAMPLE_PYTHON_PATCH
from src.providers.adapters import MockLLMAdapter
from src.providers.llm import LLMReviewProvider
from src.schemas.findings import FindingProvenance
from src.schemas.reviews import ReviewStatus


@pytest.mark.asyncio
async def test_composite_review_combines_deterministic_and_ai_findings(db_session: AsyncSession):
    """
    Verifies that the orchestrator executes both deterministic checks and AI review,
    combines results cleanly, and preserves distinct provenance tiers.
    """
    gh_client = MockGitHubClient()

    # Mock AI provider finding targeting a valid modified line in SAMPLE_PYTHON_PATCH (src/calculator.py line 13)
    ai_payload = {
        "findings": [
            {
                "rule_id": "PERF_OPTIMIZATION",
                "severity": "low",
                "category": "code_quality",
                "file_path": "src/calculator.py",
                "start_line": 13,
                "end_line": 13,
                "title": "Type check micro-optimization",
                "explanation": "Type checks can be optimized.",
                "suggested_fix": "Use type annotations.",
            }
        ]
    }
    llm_provider = LLMReviewProvider(adapter=MockLLMAdapter(mock_response=ai_payload))

    orchestrator = AnalysisOrchestrator(
        db=db_session,
        github_client=gh_client,
        llm_provider=llm_provider,
    )

    review = await orchestrator.run_review("https://github.com/my-org/backend-service", 99)

    assert review.status == ReviewStatus.COMPLETED
    assert review.summary.rule_provider_status == "completed"
    assert review.summary.ai_provider_status == "completed"
    assert review.summary.ai_provider_name == "mock"

    # Both tiers must be present
    assert review.summary.deterministic_count > 0
    assert review.summary.ai_hypothesis_count == 1
    assert review.summary.total_findings == review.summary.deterministic_count + 1

    sources = {f.source for f in review.findings}
    assert FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS in sources
    assert FindingProvenance.AI_GENERATED_HYPOTHESIS in sources


@pytest.mark.asyncio
async def test_composite_orchestrator_deduplicates_overlapping_findings(db_session: AsyncSession):
    """
    Verifies that when AI flags the exact same line and category as a deterministic rule,
    the deterministic static analysis finding takes precedence.
    """
    gh_client = MockGitHubClient()

    # In SAMPLE_PYTHON_PATCH, line 12 in src/calculator.py triggers PY005 (test_suggestion).
    # If the AI also reports test_suggestion on line 12, it should be deduplicated.
    duplicate_ai_payload = {
        "findings": [
            {
                "rule_id": "AI_MISSING_TESTS",
                "severity": "info",
                "category": "test_suggestion",
                "file_path": "src/calculator.py",
                "start_line": 12,
                "end_line": 12,
                "title": "Missing test suite",
                "explanation": "Duplicate of deterministic rule PY005.",
            }
        ]
    }
    llm_provider = LLMReviewProvider(adapter=MockLLMAdapter(mock_response=duplicate_ai_payload))

    orchestrator = AnalysisOrchestrator(
        db=db_session,
        github_client=gh_client,
        llm_provider=llm_provider,
    )

    review = await orchestrator.run_review("https://github.com/my-org/backend-service", 99)

    # The duplicate AI finding on line 12 should have been discarded in favor of PY005
    findings_on_line_12 = [
        f for f in review.findings
        if f.file_path == "src/calculator.py" and f.start_line == 12 and f.category.value == "test_suggestion"
    ]
    assert len(findings_on_line_12) == 1
    assert findings_on_line_12[0].source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert findings_on_line_12[0].rule_id == "PY005"


@pytest.mark.asyncio
async def test_composite_orchestrator_fallback_on_ai_failure(db_session: AsyncSession):
    """
    Verifies that if the AI provider fails (timeout, rate limit, unavailable),
    the orchestrator continues, records the failure, and returns all deterministic findings.
    """
    gh_client = MockGitHubClient()

    # Simulate AI timeout failure
    failing_llm = LLMReviewProvider(adapter=MockLLMAdapter(simulate_timeout=True))

    orchestrator = AnalysisOrchestrator(
        db=db_session,
        github_client=gh_client,
        llm_provider=failing_llm,
    )

    review = await orchestrator.run_review("https://github.com/my-org/backend-service", 99)

    # Review status remains COMPLETED with degraded AI status
    assert review.status == ReviewStatus.COMPLETED
    assert review.error_code == "AI_PROVIDER_DEGRADED"
    assert review.summary.ai_provider_status == "failed"
    assert "timeout" in review.summary.ai_error_sanitized.lower()


    # Deterministic findings are completely intact
    assert review.summary.deterministic_count > 0
    assert review.summary.ai_hypothesis_count == 0
    assert len(review.findings) == review.summary.deterministic_count


@pytest.mark.asyncio
async def test_composite_orchestrator_offline_mode_when_provider_none(db_session: AsyncSession, monkeypatch):
    """
    Verifies that when LLM_PROVIDER=none, the system runs purely offline with 0 LLM calls.
    """
    monkeypatch.setattr(settings, "LLM_PROVIDER", "none")
    gh_client = MockGitHubClient()

    orchestrator = AnalysisOrchestrator(
        db=db_session,
        github_client=gh_client,
    )
    assert orchestrator.llm_provider is None

    review = await orchestrator.run_review("https://github.com/my-org/backend-service", 99)

    assert review.status == ReviewStatus.COMPLETED
    assert review.error_code is None
    assert review.summary.rule_provider_status == "completed"
    assert review.summary.ai_provider_status == "disabled"
    assert review.summary.ai_hypothesis_count == 0
    assert review.summary.deterministic_count > 0


@pytest.mark.asyncio
async def test_composite_orchestrator_fallback_on_malformed_json(db_session: AsyncSession):
    """
    Verifies that when AI returns malformed or invalid JSON,
    deterministic static analysis findings remain completely available.
    """
    gh_client = MockGitHubClient()
    malformed_llm = LLMReviewProvider(adapter=MockLLMAdapter(simulate_malformed=True))

    orchestrator = AnalysisOrchestrator(
        db=db_session,
        github_client=gh_client,
        llm_provider=malformed_llm,
    )

    review = await orchestrator.run_review("https://github.com/my-org/backend-service", 99)

    assert review.status == ReviewStatus.COMPLETED
    assert review.error_code == "AI_PROVIDER_DEGRADED"
    assert review.summary.ai_provider_status == "failed"
    assert "not valid json" in review.summary.ai_error_sanitized.lower()
    assert review.summary.deterministic_count > 0
    assert len(review.findings) == review.summary.deterministic_count


@pytest.mark.asyncio
async def test_composite_orchestrator_fallback_on_unavailable_provider(db_session: AsyncSession):
    """
    Verifies that when AI provider service is 503 unavailable,
    deterministic static analysis findings remain completely available.
    """
    gh_client = MockGitHubClient()
    unavailable_llm = LLMReviewProvider(adapter=MockLLMAdapter(simulate_unavailable=True))

    orchestrator = AnalysisOrchestrator(
        db=db_session,
        github_client=gh_client,
        llm_provider=unavailable_llm,
    )

    review = await orchestrator.run_review("https://github.com/my-org/backend-service", 99)

    assert review.status == ReviewStatus.COMPLETED
    assert review.error_code == "AI_PROVIDER_DEGRADED"
    assert review.summary.ai_provider_status == "failed"
    assert "unavailable" in review.summary.ai_error_sanitized.lower()
    assert review.summary.deterministic_count > 0
    assert len(review.findings) == review.summary.deterministic_count


@pytest.mark.asyncio
async def test_composite_orchestrator_secrets_not_exposed_in_summary(db_session: AsyncSession):
    """
    Verifies that sensitive tokens or API keys present in raw provider errors
    are completely sanitized and never exposed in ReviewSummary or error_code.
    """
    gh_client = MockGitHubClient()
    secret_key = "sk-proj-super-secret-token-12345"
    failing_adapter = MockLLMAdapter(
        simulate_auth_error=True,
        api_key=secret_key,
    )
    llm_provider = LLMReviewProvider(adapter=failing_adapter)

    orchestrator = AnalysisOrchestrator(
        db=db_session,
        github_client=gh_client,
        llm_provider=llm_provider,
    )

    review = await orchestrator.run_review("https://github.com/my-org/backend-service", 99)

    assert review.status == ReviewStatus.COMPLETED
    assert review.error_code == "AI_PROVIDER_DEGRADED"
    # Ensure raw secret is NOT in sanitized error or summary
    assert secret_key not in (review.summary.ai_error_sanitized or "")
    assert secret_key not in (review.error_code or "")

