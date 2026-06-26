"""Tests for the /health endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok_or_degraded(client: AsyncClient) -> None:
    """Health endpoint always responds 200 or 503 — never crashes."""
    response = await client.get("/health")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "status" in body
    assert body["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_health_includes_db_and_redis_keys(client: AsyncClient) -> None:
    """Health response always includes db and redis keys."""
    response = await client.get("/health")
    body = response.json()
    assert "db" in body
    assert "redis" in body
    assert body["db"] in ("ok", "error")
    assert body["redis"] in ("ok", "error")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_all_green_with_services(client: AsyncClient) -> None:
    """Full green health check — requires Postgres + Redis to be running."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "db": "ok", "redis": "ok"}
