"""Unit tests for configuration validation."""
import pytest
from pydantic import ValidationError
from src.core.config import Settings


def test_default_settings():
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        LLM_PROVIDER="none",
    )
    assert settings.APP_NAME == "Patchwise API"
    assert settings.LLM_PROVIDER == "none"
    assert settings.MAX_FILES_PER_REVIEW == 20
    assert settings.MAX_PATCH_CHARS == 80000
    assert "http://localhost:3000" in settings.CORS_ORIGINS


def test_cors_origins_parsing():
    settings_str = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        CORS_ORIGINS="http://foo.com, http://bar.com",
    )
    assert settings_str.CORS_ORIGINS == ["http://foo.com", "http://bar.com"]

    settings_json = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        CORS_ORIGINS='["http://custom.local"]',
    )
    assert settings_json.CORS_ORIGINS == ["http://custom.local"]


def test_invalid_llm_provider():
    with pytest.raises(ValidationError):
        Settings(
            DATABASE_URL="sqlite+aiosqlite:///:memory:",
            LLM_PROVIDER="unsupported_provider",
        )
