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
    from .core.security import is_production_environment
    if is_production_environment():
        if not settings.API_SECRET_KEY or not settings.API_SECRET_KEY.strip():
            logger.error(
                "FATAL: Application started in production environment (%s) without API_SECRET_KEY.",
                settings.ENVIRONMENT,
            )
            raise RuntimeError(
                f"Security configuration error: API_SECRET_KEY must be configured when running in '{settings.ENVIRONMENT}'. "
                "Refusing to start in an insecure fail-open state."
            )

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

from starlette.middleware.base import BaseHTTPMiddleware
from .core.errors import ErrorCode, PatchwiseAPIException, sanitize_secret_text


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces maximum incoming HTTP request payload limits against DoS attacks."""

    def __init__(self, app, max_bytes: int = 2 * 1024 * 1024):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length_val = int(content_length)
                if length_val < 0:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "error": {
                                "code": "BAD_REQUEST",
                                "message": "Invalid negative Content-Length header.",
                            }
                        },
                    )
                if length_val > self.max_bytes:
                    return JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={
                            "error": {
                                "code": "REQUEST_ENTITY_TOO_LARGE",
                                "message": f"Request payload size ({length_val} bytes) exceeds allowed limit ({self.max_bytes} bytes).",
                            }
                        },
                    )
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": {
                            "code": "BAD_REQUEST",
                            "message": "Malformed Content-Length header.",
                        }
                    },
                )
        return await call_next(request)


# Request size limiting middleware (defense against memory exhaustion/DoS)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.MAX_REQUEST_BODY_BYTES)

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
    sanitized_msg = sanitize_secret_text(str(exc))
    logger.error("Unhandled server error: %s", sanitized_msg, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An internal server error occurred.",
                "details": sanitized_msg if settings.ENVIRONMENT == "development" else None,
            }
        },
    )
