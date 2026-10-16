"""Application Configuration for Patchwise API."""
import json
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized, validated environment configuration."""
    model_config = SettingsConfigDict(
        env_file=(".env", "services/api/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    APP_NAME: str = "Patchwise API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/patchwise",
        description="Async database connection string. Accepts postgresql+asyncpg:// or sqlite+aiosqlite:///"
    )
    DB_ECHO: bool = False

    # GitHub Client Credentials (Optional; unauthenticated allows 60 req/hr)
    GITHUB_TOKEN: Optional[str] = Field(
        default=None,
        description="Optional personal access token for higher rate limits (5,000 req/hr)."
    )

    # Review Engine Limits
    MAX_FILES_PER_REVIEW: int = Field(default=20, ge=1, le=100)
    MAX_PATCH_CHARS: int = Field(default=80000, ge=1000, le=500000)

    # AI Review Provider Configuration
    LLM_PROVIDER: str = Field(
        default="none",
        description="Active LLM provider: 'none' (deterministic rule-only mode), 'openai', 'anthropic', 'gemini', 'ollama'."
    )
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: Optional[str] = None

    # Security & CORS Settings
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
        description="Allowed origins for CORS."
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        raw_list: List[str] = []
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    raw_list = json.loads(v_stripped)
                except Exception:
                    raw_list = [origin.strip() for origin in v_stripped.split(",") if origin.strip()]
            else:
                raw_list = [origin.strip() for origin in v_stripped.split(",") if origin.strip()]
        elif isinstance(v, list):
            raw_list = [str(item).strip() for item in v]
        else:
            raw_list = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"]

        if not raw_list:
            raise ValueError("CORS_ORIGINS cannot be empty.")

        import urllib.parse
        validated: List[str] = []
        for origin in raw_list:
            origin_str = origin.strip()
            if origin_str == "*":
                raise ValueError("Wildcard origin '*' is not allowed when allow_credentials=True.")
            parsed = urllib.parse.urlparse(origin_str)
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Malformed CORS origin '{origin_str}': Scheme must be http or https.")
            if not parsed.netloc:
                raise ValueError(f"Malformed CORS origin '{origin_str}': Missing host.")
            if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
                raise ValueError(f"Malformed CORS origin '{origin_str}': Origin must not include path, query, or fragment.")

            clean_origin = f"{parsed.scheme}://{parsed.netloc}"
            validated.append(clean_origin)

        return validated

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        valid_providers = {"none", "openai", "anthropic", "gemini", "ollama", "mock"}
        lower_v = v.strip().lower()
        if lower_v not in valid_providers:
            raise ValueError(f"Invalid LLM_PROVIDER '{v}'. Must be one of {valid_providers}")
        return lower_v


settings = Settings()
