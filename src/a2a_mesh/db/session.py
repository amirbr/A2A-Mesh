"""Async SQLAlchemy session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from a2a_mesh.config import settings

# NullPool in tests: each request gets a fresh connection, no cross-event-loop issues
_pool_kwargs = {"poolclass": NullPool} if settings.app_env == "test" else {"pool_pre_ping": True}

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    **_pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session
