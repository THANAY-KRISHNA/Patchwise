from datetime import datetime, timezone
import json
import pytest
import httpx
from httpx import Response, Request

from src.analyzer.base import CandidateFinding
from src.core.errors import (
    ErrorCode,
    LLMAuthenticationError,
    LLMMalformedResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseSizeExceededError,
    LLMTimeoutError,
    sanitize_secret_text,
)
from src.github.models import GitHubPullRequest
from src.parser.diff_parser import parse_single_file_patch
from src.parser.models import ParsedDiffResult
from src.providers.adapters import (
    AnthropicAdapter,
    GeminiAdapter,
    MockLLMAdapter,
    OllamaAdapter,
    OpenAIAdapter,
)
from src.providers.base import ReviewContext
from src.providers.llm import LLMReviewProvider, get_llm_provider
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity


SAMPLE_DIFF = """--- a/src/app.py
+++ b/src/app.py
@@ -1,5 +1,7 @@
 def process_data(items):
-    return items
+    val = items[0]
+    res = int(val)
+    return res
"""


@pytest.fixture
def sample_review_context() -> ReviewContext:
    parsed_file = parse_single_file_patch(
        patch_text=SAMPLE_DIFF,
        filename="src/app.py",
        status="modified",
    )
    parsed_diff = ParsedDiffResult(
        files=[parsed_file],
        total_files=1,
        total_patch_chars=len(SAMPLE_DIFF),
    )
    pr_meta = GitHubPullRequest(
        number=42,
        title="Add data processing logic",
        body="This PR updates process_data.",
        state="open",
        html_url="https://github.com/test-org/test-repo/pull/42",
        author_username="testdev",
        base_commit_sha="aaa",
        head_commit_sha="bbb",
        base_ref="main",
        head_ref="feature",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    return ReviewContext(
        repository="test-org/test-repo",
        pr_number=42,
        pr_metadata=pr_meta,
        parsed_diff=parsed_diff,
    )


# ==============================================================================
# 1. LLMReviewProvider with MockLLMAdapter
# ==============================================================================

@pytest.mark.asyncio
async def test_llm_provider_valid_finding_enforces_ai_provenance(sample_review_context):
    """Verifies that accepted AI findings are strictly tagged AI_GENERATED_HYPOTHESIS."""
    mock_payload = {
        "findings": [
            {
                "rule_id": "BOUNDARY_CHECK",
                "severity": "high",
                "category": "boundary_condition",
                "file_path": "src/app.py",
                "start_line": 2,
                "end_line": 2,
                "title": "Unchecked list indexing",
                "explanation": "Accessing items[0] without verifying len(items) > 0 causes IndexError.",
                "suggested_fix": "Add 'if not items: return None' check.",
            }
        ]
    }
    adapter = MockLLMAdapter(mock_response=mock_payload)
    provider = LLMReviewProvider(adapter=adapter)

    result = await provider.review(sample_review_context)

    assert result.status == "completed"
    assert result.provider_name == "mock"
    assert len(result.findings) == 1

    finding = result.findings[0]
    # Enforces AI_GENERATED_HYPOTHESIS regardless of input
    assert finding.source == FindingProvenance.AI_GENERATED_HYPOTHESIS
    assert finding.rule_id == "AI_BOUNDARY_CHECK"
    assert finding.severity == FindingSeverity.HIGH
    assert finding.category == FindingCategory.BOUNDARY_CONDITION
    assert finding.file_path == "src/app.py"
    assert finding.start_line == 2


@pytest.mark.asyncio
async def test_llm_provider_rejects_ungrounded_and_fabricated_locations(sample_review_context):
    """Verifies that line grounding validator rejects out-of-hunk and non-existent files."""
    mock_payload = {
        "findings": [
            {
                "rule_id": "FABRICATED_LINE",
                "file_path": "src/app.py",
                "start_line": 999,  # Line 999 does not exist in the diff!
                "end_line": 999,
                "title": "Hallucinated line",
                "explanation": "Out of hunk line.",
            },
            {
                "rule_id": "FABRICATED_FILE",
                "file_path": "nonexistent/secret.py",  # File not in diff!
                "start_line": 1,
                "end_line": 1,
                "title": "Hallucinated file",
                "explanation": "File not in PR.",
            },
            {
                "rule_id": "VALID_FINDING",
                "file_path": "src/app.py",
                "start_line": 3,  # Valid added line in diff
                "end_line": 3,
                "title": "Potential ValueError",
                "explanation": "int(val) may fail if not a valid integer.",
            },
        ]
    }
    adapter = MockLLMAdapter(mock_response=mock_payload)
    provider = LLMReviewProvider(adapter=adapter)

    result = await provider.review(sample_review_context)

    assert result.status == "completed"
    assert result.raw_findings_count == 3
    # Exactly 1 grounded finding accepted; 2 rejected
    assert result.grounded_findings_count == 1
    assert len(result.findings) == 1
    assert result.findings[0].start_line == 3
    assert result.findings[0].rule_id == "AI_VALID_FINDING"


@pytest.mark.asyncio
async def test_llm_provider_strips_markdown_code_fences(sample_review_context):
    """Verifies that JSON responses wrapped in markdown code blocks are parsed cleanly."""
    markdown_wrapped = """```json
{
  "findings": [
    {
      "rule_id": "PARSE_TEST",
      "severity": "medium",
      "file_path": "src/app.py",
      "start_line": 2,
      "end_line": 2,
      "title": "Wrapped JSON",
      "explanation": "Markdown backticks should be stripped."
    }
  ]
}
```"""
    adapter = MockLLMAdapter(mock_response=markdown_wrapped)
    provider = LLMReviewProvider(adapter=adapter)

    result = await provider.review(sample_review_context)
    assert result.status == "completed"
    assert len(result.findings) == 1


@pytest.mark.asyncio
async def test_llm_provider_handles_malformed_json_gracefully(sample_review_context):
    """Verifies that invalid/unparseable JSON does not crash the provider or reveal raw errors."""
    adapter = MockLLMAdapter(simulate_malformed=True)
    provider = LLMReviewProvider(adapter=adapter)

    result = await provider.review(sample_review_context)
    assert result.status == "failed"
    assert len(result.findings) == 0
    assert "not valid JSON" in result.error_message


@pytest.mark.asyncio
async def test_llm_provider_handles_timeout_gracefully(sample_review_context):
    """Verifies that request timeouts return status=failed with clean sanitized messages."""
    adapter = MockLLMAdapter(simulate_timeout=True)
    provider = LLMReviewProvider(adapter=adapter)

    result = await provider.review(sample_review_context)
    assert result.status == "failed"
    assert len(result.findings) == 0
    assert "timeout" in result.error_message.lower()



@pytest.mark.asyncio
async def test_llm_provider_handles_rate_limiting_gracefully(sample_review_context):
    """Verifies rate limits return status=failed with clean sanitized message."""
    adapter = MockLLMAdapter(simulate_rate_limit=True)
    provider = LLMReviewProvider(adapter=adapter)

    result = await provider.review(sample_review_context)
    assert result.status == "failed"
    assert "rate limit" in result.error_message.lower()


# ==============================================================================
# 2. Provider Adapters and Mock HTTP Transport Verification
# ==============================================================================

@pytest.mark.asyncio
async def test_openai_adapter_http_request_and_extraction():
    """Verifies OpenAIAdapter sends correct chat completion payload and extracts choices[0].message.content."""
    def handler(request: Request) -> Response:
        assert request.url == "https://api.openai.com/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-sk-12345"
        body = json.loads(request.content)
        assert body["model"] == "gpt-4o"
        assert body["response_format"] == {"type": "json_object"}
        assert len(body["messages"]) == 2

        resp_content = json.dumps({"findings": [{"rule_id": "OAI_1", "file_path": "a.py"}]})
        return Response(
            200,
            json={"choices": [{"message": {"content": resp_content}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIAdapter(api_key="test-sk-12345", model="gpt-4o")

    result = await adapter.execute("sys prompt", "user prompt", client=client)
    parsed = json.loads(result)
    assert "findings" in parsed
    assert parsed["findings"][0]["rule_id"] == "OAI_1"


@pytest.mark.asyncio
async def test_anthropic_adapter_http_request_and_extraction():
    """Verifies AnthropicAdapter sends correct messages payload and extracts content[0].text."""
    def handler(request: Request) -> Response:
        assert request.url == "https://api.anthropic.com/v1/messages"
        assert request.headers["x-api-key"] == "test-ant-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        body = json.loads(request.content)
        assert body["model"] == "claude-3-5-sonnet-20241022"
        assert body["system"] == "sys prompt"
        assert body["messages"][0]["content"] == "user prompt"

        resp_content = json.dumps({"findings": [{"rule_id": "ANT_1"}]})
        return Response(
            200,
            json={"content": [{"text": resp_content}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = AnthropicAdapter(api_key="test-ant-key")

    result = await adapter.execute("sys prompt", "user prompt", client=client)
    parsed = json.loads(result)
    assert parsed["findings"][0]["rule_id"] == "ANT_1"


@pytest.mark.asyncio
async def test_gemini_adapter_http_request_and_extraction():
    """Verifies GeminiAdapter sends correct generateContent payload and extracts parts[0].text."""
    def handler(request: Request) -> Response:
        assert "models/gemini-1.5-pro:generateContent" in str(request.url)
        assert request.headers["x-goog-api-key"] == "test-gemini-key"
        body = json.loads(request.content)
        assert body["generationConfig"]["response_mime_type"] == "application/json"

        resp_content = json.dumps({"findings": [{"rule_id": "GEM_1"}]})
        return Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": resp_content}]}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = GeminiAdapter(api_key="test-gemini-key", model="gemini-1.5-pro")

    result = await adapter.execute("sys prompt", "user prompt", client=client)
    parsed = json.loads(result)
    assert parsed["findings"][0]["rule_id"] == "GEM_1"


@pytest.mark.asyncio
async def test_ollama_adapter_http_request_and_extraction():
    """Verifies OllamaAdapter sends correct chat payload to localhost."""
    def handler(request: Request) -> Response:
        assert request.url == "http://localhost:11434/api/chat"
        body = json.loads(request.content)
        assert body["model"] == "llama3"
        assert body["format"] == "json"

        resp_content = json.dumps({"findings": [{"rule_id": "OLLAMA_1"}]})
        return Response(200, json={"message": {"content": resp_content}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OllamaAdapter(model="llama3")

    result = await adapter.execute("sys prompt", "user prompt", client=client)
    parsed = json.loads(result)
    assert parsed["findings"][0]["rule_id"] == "OLLAMA_1"


@pytest.mark.asyncio
async def test_adapter_missing_api_key_raises_auth_error():
    """Verifies missing API keys raise clear LLMAuthenticationError."""
    adapter = OpenAIAdapter(api_key=None)
    with pytest.raises(LLMAuthenticationError) as exc_info:
        await adapter.execute("sys", "user")
    assert "Missing API key" in str(exc_info.value)


@pytest.mark.asyncio
async def test_adapter_auth_failure_sanitizes_secret():
    """Verifies 401 Unauthorized errors never leak raw secret keys in exception messages."""
    secret = "sk-secret-token-abcdef12345"

    def handler(request: Request) -> Response:
        return Response(401, text=f"Unauthorized: token {secret} was rejected")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIAdapter(api_key=secret)

    with pytest.raises(LLMAuthenticationError) as exc_info:
        await adapter.execute("sys", "user", client=client)

    err_text = str(exc_info.value)
    assert secret not in err_text


@pytest.mark.asyncio
async def test_adapter_response_size_limit_enforced():
    """Verifies responses exceeding max_response_chars are rejected."""
    huge_text = "x" * 2000

    def handler(request: Request) -> Response:
        return Response(200, text=huge_text)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIAdapter(api_key="valid-key", max_response_chars=1000)

    with pytest.raises(LLMResponseSizeExceededError) as exc_info:
        await adapter.execute("sys", "user", client=client)

    assert "exceeded limit" in str(exc_info.value)
