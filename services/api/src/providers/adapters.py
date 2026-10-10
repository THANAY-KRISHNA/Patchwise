"""LLM Provider Adapters for Patchwise.

Implements structured HTTP adapters for OpenAI, Anthropic, Gemini, Ollama, and Mock providers.
Enforces request timeouts, bounded retries, response size limits, and secret sanitization.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx

from ..core.errors import (
    ErrorCode,
    LLMAuthenticationError,
    LLMMalformedResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseSizeExceededError,
    LLMSchemaValidationError,
    LLMTimeoutError,
    sanitize_secret_text,
)

logger = logging.getLogger(__name__)


class BaseLLMAdapter:
    """Base class for all remote LLM service adapters."""

    def __init__(
        self,
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        max_response_chars: int = 100000,
    ):
        self.provider_name = provider_name
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_response_chars = max_response_chars

    def _prepare_request(
        self, system_prompt: str, user_prompt: str
    ) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        """Construct (endpoint_url, headers, json_payload) for the provider API."""
        raise NotImplementedError

    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """Extract the model's generated text content from the parsed JSON response."""
        raise NotImplementedError

    async def execute(
        self,
        system_prompt: str,
        user_prompt: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> str:
        """
        Execute request with bounded retries, strict timeouts, response size limits,
        and secret-sanitized error handling.
        """
        # Credentials validation for providers that require an API key
        if self.provider_name in ("openai", "anthropic", "gemini") and not self.api_key:
            raise LLMAuthenticationError(
                f"Missing API key for provider '{self.provider_name}'. Set LLM_API_KEY environment variable."
            )

        endpoint, headers, payload = self._prepare_request(system_prompt, user_prompt)
        timeout = httpx.Timeout(self.timeout_seconds, connect=10.0)

        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=timeout)
            should_close_client = True

        last_error: Optional[Exception] = None

        try:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(endpoint, headers=headers, json=payload)

                    # Check for rate limiting
                    if response.status_code == 429:
                        if attempt < self.max_retries:
                            await asyncio.sleep(0.05 * (2 ** attempt))
                            continue
                        raise LLMRateLimitError(
                            f"Rate limit exceeded on {self.provider_name} API (HTTP 429)."
                        )

                    # Check for authentication failures
                    if response.status_code in (401, 403):
                        raise LLMAuthenticationError(
                            f"Authentication failed on {self.provider_name} API (HTTP {response.status_code})."
                        )

                    # Check for transient server errors
                    if response.status_code in (500, 502, 503, 504):
                        if attempt < self.max_retries:
                            await asyncio.sleep(0.05 * (2 ** attempt))
                            continue
                        raise LLMProviderError(
                            f"{self.provider_name} service unavailable (HTTP {response.status_code}).",
                            error_code=ErrorCode.AI_PROVIDER_UNAVAILABLE,
                            status_code=response.status_code,
                            secret_to_scrub=self.api_key,
                        )

                    # Check other 4xx errors
                    if response.status_code >= 400:
                        raise LLMProviderError(
                            f"{self.provider_name} returned client error (HTTP {response.status_code}).",
                            error_code=ErrorCode.AI_PROVIDER_UNAVAILABLE,
                            status_code=response.status_code,
                            secret_to_scrub=self.api_key,
                        )

                    # Check response size before full extraction
                    raw_text = response.text
                    if len(raw_text) > self.max_response_chars:
                        raise LLMResponseSizeExceededError(
                            f"{self.provider_name} response ({len(raw_text)} chars) exceeded limit ({self.max_response_chars})."
                        )

                    # Parse JSON envelope
                    try:
                        resp_data = response.json()
                    except Exception as json_err:
                        raise LLMMalformedResponseError(
                            f"Failed to parse JSON envelope from {self.provider_name}: {str(json_err)}"
                        )

                    # Extract model output
                    try:
                        content = self._extract_content(resp_data)
                    except Exception as ext_err:
                        raise LLMMalformedResponseError(
                            f"Unexpected response structure from {self.provider_name}: {str(ext_err)}"
                        )

                    if len(content) > self.max_response_chars:
                        raise LLMResponseSizeExceededError(
                            f"Model content size ({len(content)} chars) exceeded safe threshold."
                        )

                    return content

                except (httpx.TimeoutException, TimeoutError) as timeout_err:
                    last_error = timeout_err
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.05 * (2 ** attempt))
                        continue
                    raise LLMTimeoutError(
                        f"Request to {self.provider_name} timed out after {self.timeout_seconds}s."
                    )

                except httpx.NetworkError as net_err:
                    last_error = net_err
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.05 * (2 ** attempt))
                        continue
                    raise LLMProviderError(
                        f"Network connectivity error contacting {self.provider_name}: {sanitize_secret_text(str(net_err), self.api_key)}",
                        error_code=ErrorCode.AI_PROVIDER_UNAVAILABLE,
                        secret_to_scrub=self.api_key,
                    )

            if last_error:
                raise LLMProviderError(
                    f"Exhausted retries contacting {self.provider_name}: {sanitize_secret_text(str(last_error), self.api_key)}",
                    error_code=ErrorCode.AI_PROVIDER_UNAVAILABLE,
                    secret_to_scrub=self.api_key,
                )
            raise LLMProviderError(f"Failed to execute review on {self.provider_name}.")

        finally:
            if should_close_client:
                await client.aclose()


class MockLLMAdapter(BaseLLMAdapter):
    """
    In-memory deterministic mock adapter for testing, simulation, and offline verification.
    Does not perform network requests.
    """

    def __init__(
        self,
        mock_response: Optional[Union[str, List[Dict[str, Any]], Dict[str, Any]]] = None,
        simulate_timeout: bool = False,
        simulate_rate_limit: bool = False,
        simulate_auth_error: bool = False,
        simulate_unavailable: bool = False,
        simulate_oversized: bool = False,
        simulate_malformed: bool = False,
        **kwargs: Any,
    ):
        super().__init__(provider_name="mock", **kwargs)
        self.mock_response = mock_response
        self.simulate_timeout = simulate_timeout
        self.simulate_rate_limit = simulate_rate_limit
        self.simulate_auth_error = simulate_auth_error
        self.simulate_unavailable = simulate_unavailable
        self.simulate_oversized = simulate_oversized
        self.simulate_malformed = simulate_malformed
        self.call_count = 0
        self.last_prompts: Optional[Tuple[str, str]] = None

    async def execute(
        self,
        system_prompt: str,
        user_prompt: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> str:
        self.call_count += 1
        self.last_prompts = (system_prompt, user_prompt)

        if self.simulate_timeout:
            raise LLMTimeoutError("Simulated mock timeout.")
        if self.simulate_rate_limit:
            raise LLMRateLimitError("Simulated mock rate limit.")
        if self.simulate_auth_error:
            raise LLMAuthenticationError("Simulated mock authentication error.")
        if self.simulate_unavailable:
            raise LLMProviderError(
                "Simulated mock service unavailable.",
                error_code=ErrorCode.AI_PROVIDER_UNAVAILABLE,
                status_code=503,
            )
        if self.simulate_oversized:
            raise LLMResponseSizeExceededError("Simulated mock response size limit exceeded.")
        if self.simulate_malformed:
            return "{ unclosed invalid json : 123"

        if self.mock_response is not None:
            if isinstance(self.mock_response, (dict, list)):
                return json.dumps(self.mock_response)
            return str(self.mock_response)

        # Default fallback: return empty findings array
        return '{"findings": []}'


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI Chat Completions API with structured JSON output."""

    def __init__(self, **kwargs: Any):
        super().__init__(provider_name="openai", **kwargs)
        self.model = self.model or "gpt-4o"
        self.base_url = self.base_url or "https://api.openai.com/v1"

    def _prepare_request(
        self, system_prompt: str, user_prompt: str
    ) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        return endpoint, headers, payload

    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        return response_data["choices"][0]["message"]["content"]


class AnthropicAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Messages API."""

    def __init__(self, **kwargs: Any):
        super().__init__(provider_name="anthropic", **kwargs)
        self.model = self.model or "claude-3-5-sonnet-20241022"
        self.base_url = self.base_url or "https://api.anthropic.com/v1"

    def _prepare_request(
        self, system_prompt: str, user_prompt: str
    ) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        endpoint = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": 0.1,
        }
        return endpoint, headers, payload

    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        return response_data["content"][0]["text"]


class GeminiAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini REST API using structured JSON output."""

    def __init__(self, **kwargs: Any):
        super().__init__(provider_name="gemini", **kwargs)
        self.model = self.model or "gemini-1.5-pro"
        self.base_url = self.base_url or "https://generativelanguage.googleapis.com/v1beta"

    def _prepare_request(
        self, system_prompt: str, user_prompt: str
    ) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        endpoint = f"{self.base_url}/models/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key or "",
            "content-type": "application/json",
        }
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }
        return endpoint, headers, payload

    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        return response_data["candidates"][0]["content"]["parts"][0]["text"]


class OllamaAdapter(BaseLLMAdapter):
    """Adapter for local Ollama server API."""

    def __init__(self, **kwargs: Any):
        super().__init__(provider_name="ollama", **kwargs)
        self.model = self.model or "llama3"
        self.base_url = self.base_url or "http://localhost:11434"

    def _prepare_request(
        self, system_prompt: str, user_prompt: str
    ) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        endpoint = f"{self.base_url}/api/chat"
        headers = {"content-type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
        }
        return endpoint, headers, payload

    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        return response_data["message"]["content"]
