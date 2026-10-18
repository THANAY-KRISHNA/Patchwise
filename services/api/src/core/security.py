"""Security dependencies and authentication checks."""
import secrets
from typing import Optional
from fastapi import Header, Request
from .config import settings
from .errors import ErrorCode, PatchwiseAPIException


def is_production_environment() -> bool:
    """Check if the current runtime environment is production or staging."""
    env = (settings.ENVIRONMENT or "").strip().lower()
    return env in ("production", "prod", "staging")


async def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> None:
    """
    Enforces API authentication for mutating and sensitive endpoints.

    Security Policy:
    1. In production / staging: API_SECRET_KEY MUST be configured.
       If missing or empty in production, requests fail closed (HTTP 401)
       to prevent accidental unauthenticated access.
    2. In development / testing: If API_SECRET_KEY is None or empty, unauthenticated
       access is allowed for developer convenience.
    3. In any environment: If API_SECRET_KEY is configured, all requests must provide
       a matching key via 'X-API-Key' or 'Authorization: Bearer <token>'.
    4. Credential comparison uses constant-time `secrets.compare_digest` to prevent timing attacks.
    5. Tokens and secrets are never logged or echoed in error responses.
    """
    configured_key = settings.API_SECRET_KEY
    is_prod = is_production_environment()

    # Fail closed in production/staging if secret key is missing or blank
    if not configured_key or not configured_key.strip():
        if is_prod:
            raise PatchwiseAPIException(
                status_code=401,
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Unauthorized: Authentication is required. API_SECRET_KEY must be configured on the server in production mode.",
            )
        # Development / testing convenience: allow unauthenticated requests
        return

    # Extract supplied credential
    supplied_key: Optional[str] = None
    if x_api_key:
        supplied_key = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        supplied_key = authorization[7:].strip()

    # Validate against configured key using constant-time comparison
    if not supplied_key or not secrets.compare_digest(supplied_key, configured_key.strip()):
        raise PatchwiseAPIException(
            status_code=401,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Unauthorized: Missing or invalid API authentication key.",
        )
