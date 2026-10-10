"""LLM Review Provider with Strict Provenance, Grounding, and Sanitization.

Coordinates LLM code analysis, parses candidate findings, strictly enforces
AI_GENERATED_HYPOTHESIS provenance, and rejects ungrounded or fabricated line numbers
using LineGroundingValidator.
"""
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx

from ..analyzer.base import CandidateFinding
from ..analyzer.registry import plugin_registry
from ..core.config import settings
from ..core.errors import (
    ErrorCode,
    LLMMalformedResponseError,
    LLMProviderError,
    LLMSchemaValidationError,
    sanitize_secret_text,
)
from ..schemas.findings import FindingCategory, FindingProvenance, FindingSeverity
from ..validator.grounding import LineGroundingValidator
from .adapters import (
    AnthropicAdapter,
    BaseLLMAdapter,
    GeminiAdapter,
    MockLLMAdapter,
    OllamaAdapter,
    OpenAIAdapter,
)
from .base import BaseReviewProvider, ReviewContext, ReviewResult
from .prompts import build_review_prompt

logger = logging.getLogger(__name__)


def create_llm_adapter(
    provider_name: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_seconds: float = 30.0,
) -> BaseLLMAdapter:
    """Factory creating the appropriate BaseLLMAdapter for the given provider name."""
    clean_name = provider_name.strip().lower()

    if clean_name == "mock":
        return MockLLMAdapter(timeout_seconds=timeout_seconds)
    elif clean_name == "openai":
        return OpenAIAdapter(
            api_key=api_key or settings.LLM_API_KEY,
            model=model or settings.LLM_MODEL,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
    elif clean_name == "anthropic":
        return AnthropicAdapter(
            api_key=api_key or settings.LLM_API_KEY,
            model=model or settings.LLM_MODEL,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
    elif clean_name == "gemini":
        return GeminiAdapter(
            api_key=api_key or settings.LLM_API_KEY,
            model=model or settings.LLM_MODEL,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
    elif clean_name == "ollama":
        return OllamaAdapter(
            model=model or settings.LLM_MODEL,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
    elif clean_name == "none":
        raise ValueError("Provider 'none' has no LLM adapter; use RuleOnlyProvider.")
    else:
        raise ValueError(f"Unsupported LLM provider '{provider_name}'.")


class LLMReviewProvider(BaseReviewProvider):
    """
    AI-powered Pull Request Review Provider.
    Invokes external LLMs via structured adapters, parses output, and validates every finding.
    Guarantees that all findings are tagged as AI_GENERATED_HYPOTHESIS and grounded in modified lines.
    """

    def __init__(
        self,
        provider_id: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        adapter: Optional[BaseLLMAdapter] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout_seconds: float = 30.0,
    ):
        self.http_client = http_client
        if adapter is not None:
            self.adapter = adapter
        else:
            resolved_provider = provider_id or settings.LLM_PROVIDER
            if resolved_provider == "none":
                resolved_provider = "mock"
            self.adapter = create_llm_adapter(
                provider_name=resolved_provider,
                api_key=api_key,
                model=model,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
            )

    @property
    def provider_id(self) -> str:
        return self.adapter.provider_name

    def _strip_code_fences(self, text: str) -> str:
        """Strip markdown code fence blocks if returned by the model."""
        stripped = text.strip()
        if stripped.startswith("```json"):
            stripped = stripped[7:]
        elif stripped.startswith("```"):
            stripped = stripped[3:]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        return stripped.strip()

    def _parse_candidate_finding(self, item: Dict[str, Any]) -> CandidateFinding:
        """
        Parses a single finding dictionary into a CandidateFinding.
        Strictly enforces AI_GENERATED_HYPOTHESIS provenance and provisional severities.
        """
        raw_rule = str(item.get("rule_id", "AI_HYPOTHESIS")).strip()
        if not raw_rule.startswith("AI_"):
            rule_id = f"AI_{raw_rule}"
        else:
            rule_id = raw_rule

        # Parse severity (provisional, default MEDIUM)
        raw_sev = str(item.get("severity", "medium")).lower().strip()
        try:
            severity = FindingSeverity(raw_sev)
        except ValueError:
            severity = FindingSeverity.MEDIUM

        # Parse category (default CODE_QUALITY)
        raw_cat = str(item.get("category", "code_quality")).lower().strip()
        try:
            category = FindingCategory(raw_cat)
        except ValueError:
            category = FindingCategory.CODE_QUALITY

        # Line numbers
        start_line = item.get("start_line")
        end_line = item.get("end_line")
        if start_line is not None:
            try:
                start_line = int(start_line)
            except (ValueError, TypeError):
                start_line = None
        if end_line is not None:
            try:
                end_line = int(end_line)
            except (ValueError, TypeError):
                end_line = None

        file_path = str(item.get("file_path", "")).strip()
        title = str(item.get("title", "AI-detected potential issue")).strip()
        explanation = str(item.get("explanation", "Potential issue identified by AI review model.")).strip()
        suggested_fix = item.get("suggested_fix")
        if suggested_fix is not None:
            suggested_fix = str(suggested_fix).strip()

        # CRITICAL MANDATE: Never trust LLM-claimed provenance. Always assign AI_GENERATED_HYPOTHESIS.
        return CandidateFinding(
            rule_id=rule_id,
            source=FindingProvenance.AI_GENERATED_HYPOTHESIS,
            severity=severity,
            category=category,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            title=title,
            explanation=explanation,
            suggested_fix=suggested_fix,
        )

    def _parse_and_validate_response(
        self, raw_content: str, context: ReviewContext
    ) -> Tuple[List[CandidateFinding], int]:
        """
        Parses JSON content, validates schema, and applies line grounding validation.
        Returns: (accepted_candidates, total_raw_candidates)
        """
        cleaned = self._strip_code_fences(raw_content)
        if not cleaned:
            return [], 0

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as err:
            raise LLMMalformedResponseError(
                f"Model response is not valid JSON: {str(err)}"
            )

        items: List[Any] = []
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            if "findings" in parsed and isinstance(parsed["findings"], list):
                items = parsed["findings"]
            elif "candidates" in parsed and isinstance(parsed["candidates"], list):
                items = parsed["candidates"]
            else:
                raise LLMSchemaValidationError(
                    "Model response JSON object must contain a 'findings' or 'candidates' array."
                )
        else:
            raise LLMSchemaValidationError("Model response must be a JSON array or object.")

        raw_candidates: List[CandidateFinding] = []
        for it in items:
            if isinstance(it, dict):
                raw_candidates.append(self._parse_candidate_finding(it))

        # Grounding validation against diff line set
        validator = LineGroundingValidator(context.parsed_diff)
        accepted_candidates: List[CandidateFinding] = []
        seen_fingerprints = set()

        for candidate in raw_candidates:
            # Enforce line-grounding on modified lines
            val_result = validator.validate_finding(
                candidate,
                require_changed_line=True,
                allow_file_level=False,
            )

            if val_result.is_valid:
                fp_data = f"{candidate.rule_id}:{candidate.file_path}:{candidate.start_line}:{candidate.end_line}:{candidate.title}"
                fingerprint = hashlib.sha256(fp_data.encode("utf-8")).hexdigest()
                if fingerprint not in seen_fingerprints:
                    seen_fingerprints.add(fingerprint)
                    accepted_candidates.append(candidate)
            else:
                logger.debug(
                    f"Rejected ungrounded AI finding: {candidate.file_path}:{candidate.start_line} - {val_result.rejection_reason}"
                )

        return accepted_candidates, len(raw_candidates)

    async def review(self, context: ReviewContext) -> ReviewResult:
        """
        Execute AI review against the given ReviewContext with full exception isolation.
        """
        start_time = time.perf_counter()

        # Collect language-specific context from active plugins
        lang_contexts: List[str] = []
        for f in context.parsed_diff.files:
            analyzer = plugin_registry.get_analyzer_for_file(f.file_path)
            if analyzer:
                ctx_text = analyzer.get_language_prompt_context()
                if ctx_text and ctx_text not in lang_contexts:
                    lang_contexts.append(ctx_text)

        language_context = "\n\n".join(lang_contexts)
        system_prompt, user_prompt = build_review_prompt(context, language_context=language_context)

        try:
            raw_content = await self.adapter.execute(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                client=self.http_client,
            )

            accepted_findings, raw_count = self._parse_and_validate_response(
                raw_content=raw_content, context=context
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            return ReviewResult(
                provider_name=self.provider_id,
                findings=accepted_findings,
                raw_findings_count=raw_count,
                grounded_findings_count=len(accepted_findings),
                duration_ms=elapsed_ms,
                status="completed",
                error_message=None,
            )

        except LLMProviderError as err:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(f"AI review provider failure ({self.provider_id}): {err.sanitized_message}")
            return ReviewResult(
                provider_name=self.provider_id,
                findings=[],
                raw_findings_count=0,
                grounded_findings_count=0,
                duration_ms=elapsed_ms,
                status="failed",
                error_message=err.sanitized_message,
            )

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            sanitized = sanitize_secret_text(str(exc), getattr(self.adapter, "api_key", None))
            logger.exception(f"Unexpected AI provider failure ({self.provider_id}): {sanitized}")
            return ReviewResult(
                provider_name=self.provider_id,
                findings=[],
                raw_findings_count=0,
                grounded_findings_count=0,
                duration_ms=elapsed_ms,
                status="failed",
                error_message="Unexpected error during AI review execution.",
            )


def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    http_client: Optional[httpx.AsyncClient] = None,
) -> LLMReviewProvider:
    """Helper factory for obtaining configured LLMReviewProvider instances."""
    resolved_name = provider_name or settings.LLM_PROVIDER
    return LLMReviewProvider(
        provider_id=resolved_name,
        api_key=api_key,
        model=model,
        base_url=base_url,
        http_client=http_client,
    )
