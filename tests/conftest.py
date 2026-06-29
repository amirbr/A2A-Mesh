"""Shared pytest fixtures.

Environment variables are set here before app imports so tests work
without a .env file. Real secrets are never required in the test suite.
"""

import os

os.environ["APP_ENV"] = "test"  # must be set before app import to activate NullPool
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://a2a_mesh:password@localhost:5435/a2a_mesh")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://a2a_mesh:password@localhost:5436/a2a_mesh_test")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from a2a_mesh.main import app  # noqa: E402


@pytest.fixture()
async def client() -> AsyncClient:
    """Async HTTP client wired to the FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
