"""Health Probes and Status Routers."""
from datetime import datetime, timezone
from fastapi import APIRouter
from ..core.config import settings
from ..db.session import check_db_connection
from ..analyzer.registry import plugin_registry
from ..schemas.health import DatabaseHealth, HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    Truthful operational health check probe.
    Reports database connectivity, active LLM provider, and plugin readiness status.
    Does not expose passwords, tokens, or private infrastructure details.
    """
    db_connected, dialect, db_error = await check_db_connection()

    status_str = "healthy" if db_connected else "degraded"

    return HealthResponse(
        status=status_str,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        database=DatabaseHealth(
            connected=db_connected,
            dialect=dialect,
            error=db_error if settings.ENVIRONMENT == "development" else None,
        ),
        llm_provider=settings.LLM_PROVIDER,
        active_plugins=[p.language_id for p in plugin_registry.list_all()],
    )
