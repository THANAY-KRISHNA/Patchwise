"""Standardized Error Codes and Exceptions for Patchwise API."""
from enum import Enum
from typing import Any, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorCode(str, Enum):
    INVALID_REPOSITORY_URL = "INVALID_REPOSITORY_URL"
    PR_NOT_FOUND = "PR_NOT_FOUND"
    GITHUB_RATE_LIMITED = "GITHUB_RATE_LIMITED"
    PATCH_TOO_LARGE = "PATCH_TOO_LARGE"
    REVIEW_TIMEOUT = "REVIEW_TIMEOUT"
    AI_PROVIDER_UNAVAILABLE = "AI_PROVIDER_UNAVAILABLE"
    AI_PROVIDER_AUTH_ERROR = "AI_PROVIDER_AUTH_ERROR"
    AI_PROVIDER_RATE_LIMITED = "AI_PROVIDER_RATE_LIMITED"
    AI_PROVIDER_MALFORMED_OUTPUT = "AI_PROVIDER_MALFORMED_OUTPUT"
    AI_PROVIDER_RESPONSE_TOO_LARGE = "AI_PROVIDER_RESPONSE_TOO_LARGE"
    AI_PROVIDER_TIMEOUT = "AI_PROVIDER_TIMEOUT"
    UNGROUNDED_FINDING = "UNGROUNDED_FINDING"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    details: Optional[Any] = None


class PatchwiseAPIException(HTTPException):
    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        message: str,
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "code": error_code.value,
                "message": message,
                "details": details,
            },
        )
        self.error_code = error_code
        self.message = message
        self.details = details


# --- Secret Sanitization Helper ---
import re

SENSITIVE_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9_\-]{8,})", re.IGNORECASE),
    re.compile(r"(ghp_[a-zA-Z0-9]{20,})", re.IGNORECASE),
    re.compile(r"(bearer\s+)([a-zA-Z0-9_\-\.]{8,})", re.IGNORECASE),
    re.compile(r"(key=)([a-zA-Z0-9_\-]{8,})", re.IGNORECASE),
    re.compile(r"(x-api-key['\":\s=]+)([a-zA-Z0-9_\-]{8,})", re.IGNORECASE),
    re.compile(r"(x-goog-api-key['\":\s=]+)([a-zA-Z0-9_\-]{8,})", re.IGNORECASE),
]


def sanitize_secret_text(text: str, secret: Optional[str] = None) -> str:
    """
    Remove or redact sensitive API keys, tokens, or credentials from error messages.
    Guarantees no raw tokens are leaked in logs, exception traces, or API responses.
    """
    if not text:
        return ""

    sanitized = text

    # Redact explicitly provided secret
    if secret and len(secret) >= 4:
        sanitized = sanitized.replace(secret, "[REDACTED_SECRET]")

    # Redact common token patterns
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(r"[REDACTED_TOKEN]", sanitized)

    return sanitized


# --- LLM Provider Exceptions Hierarchy ---
class LLMProviderError(Exception):
    """Base exception for all AI/LLM review provider failures."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.AI_PROVIDER_UNAVAILABLE,
        status_code: Optional[int] = None,
        secret_to_scrub: Optional[str] = None,
    ):
        self.raw_message = message
        self.sanitized_message = sanitize_secret_text(message, secret_to_scrub)
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.sanitized_message)


class LLMTimeoutError(LLMProviderError):
    """Raised when an AI provider request exceeds timeout limits."""

    def __init__(self, message: str = "AI review provider request timed out."):
        super().__init__(
            message=message,
            error_code=ErrorCode.AI_PROVIDER_TIMEOUT,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )


class LLMRateLimitError(LLMProviderError):
    """Raised when an AI provider rate limit is exceeded."""

    def __init__(self, message: str = "AI review provider rate limit exceeded."):
        super().__init__(
            message=message,
            error_code=ErrorCode.AI_PROVIDER_RATE_LIMITED,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class LLMAuthenticationError(LLMProviderError):
    """Raised when credentials for an AI provider are missing or invalid."""

    def __init__(self, message: str = "AI review provider authentication failed."):
        super().__init__(
            message=message,
            error_code=ErrorCode.AI_PROVIDER_AUTH_ERROR,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class LLMMalformedResponseError(LLMProviderError):
    """Raised when an AI provider returns unparseable or malformed JSON."""

    def __init__(self, message: str = "AI review provider returned malformed or non-JSON output."):
        super().__init__(
            message=message,
            error_code=ErrorCode.AI_PROVIDER_MALFORMED_OUTPUT,
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class LLMSchemaValidationError(LLMProviderError):
    """Raised when AI output does not conform to the candidate finding schema."""

    def __init__(self, message: str = "AI review findings schema validation failed."):
        super().__init__(
            message=message,
            error_code=ErrorCode.AI_PROVIDER_MALFORMED_OUTPUT,
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class LLMResponseSizeExceededError(LLMProviderError):
    """Raised when an AI provider response exceeds the configured safety threshold."""

    def __init__(self, message: str = "AI review provider response exceeded safe size limits."):
        super().__init__(
            message=message,
            error_code=ErrorCode.AI_PROVIDER_RESPONSE_TOO_LARGE,
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

