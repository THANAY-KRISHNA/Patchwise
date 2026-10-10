"""Database Session Engine and Connection Lifecycle."""
from typing import AsyncGenerator, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from ..core.config import settings

# Create async engine with pool pre-ping to detect stale connections
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> Tuple[bool, str, str | None]:
    """
    Truthful database connectivity probe.
    Returns: (is_connected: bool, dialect: str, error_message: Optional[str])
    """
    dialect_name = engine.dialect.name
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True, dialect_name, None
    except Exception as exc:
        return False, dialect_name, str(exc)
