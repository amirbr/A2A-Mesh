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

import asyncio  # noqa: E402
import socket  # noqa: E402
from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
import uvicorn  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
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


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
async def mock_mcp_server() -> AsyncIterator[str]:
    """Run a real local MCP server (streamable HTTP) with one `get_weather` tool.

    Yields the server's MCP endpoint URL. Used to prove the MCP client integration works
    against an actual server, not just mocks of the `mcp` SDK.
    """
    mcp = FastMCP("test-mcp-server")

    @mcp.tool()
    def get_weather(city: str) -> str:
        """Return a canned weather report for a city."""
        return f"sunny in {city}"

    port = _free_port()
    config = uvicorn.Config(mcp.streamable_http_app(), host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.01)

    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        await task
