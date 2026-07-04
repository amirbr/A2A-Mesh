"""Shared pytest fixtures.

Environment variables are set here before app imports so tests work
without a .env file. Real secrets are never required in the test suite.
"""

import os

os.environ["APP_ENV"] = "test"  # activates NullPool in session.py
os.environ["DATABASE_URL"] = "postgresql+asyncpg://a2a_mesh:password@localhost:5436/a2a_mesh_test"
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://a2a_mesh:password@localhost:5436/a2a_mesh_test")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ANTHROPIC_API_KEY", "placeholder")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

from a2a_mesh.db.session import AsyncSessionLocal  # noqa: E402
from a2a_mesh.db.base import Base  # noqa: E402
from a2a_mesh.db.session import engine  # noqa: E402
import a2a_mesh.db.models  # noqa: F401, E402
from a2a_mesh.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def mock_llm() -> None:
    """Patch LLM dispatch globally so no test makes a real API call."""
    with patch("a2a_mesh.llm.dispatch.complete", new_callable=AsyncMock) as m:
        m.return_value = "mocked llm response"
        yield m


@pytest.fixture(scope="session", autouse=True)
async def create_tables() -> None:
    """Create all tables in the test DB once per session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(autouse=True)
async def clean_db() -> None:
    """Truncate all data tables before each test for isolation."""
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("TRUNCATE TABLE api_keys, users, agents, tasks, pipeline_runs, pipelines, companies RESTART IDENTITY CASCADE")
        )
        await session.commit()


@pytest.fixture()
async def client() -> AsyncClient:
    """Async HTTP client wired to the FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
