"""Patchwise FastAPI Service Entry Point."""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.errors import ErrorCode, PatchwiseAPIException
from .routers import benchmarks, health, reviews
from .analyzer.registry import plugin_registry

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("patchwise.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown hooks."""
    logger.info("Initializing Patchwise API service (%s)...", settings.ENVIRONMENT)
    logger.info("Configured LLM Provider: %s", settings.LLM_PROVIDER)
    logger.info("Registered Language Plugins: %d", len(plugin_registry.list_all()))
    yield
    logger.info("Shutting down Patchwise API service...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Pull Request Review & Testing Assistant API",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# CORS Configuration: allow configured origins (e.g. localhost:3000), not wildcard *
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router)
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(reviews.router, prefix=settings.API_V1_PREFIX)
app.include_router(benchmarks.router, prefix=settings.API_V1_PREFIX)


@app.get(f"{settings.API_V1_PREFIX}/plugins", tags=["Plugins"])
async def get_plugins_overview():
    """Returns the declared readiness status of all language plugins."""
    return {"plugins": plugin_registry.get_status_overview()}


# Standardized Exception Handling
@app.exception_handler(PatchwiseAPIException)
async def patchwise_exception_handler(request: Request, exc: PatchwiseAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code.value,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server error: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An internal server error occurred.",
                "details": str(exc) if settings.ENVIRONMENT == "development" else None,
            }
        },
    )
