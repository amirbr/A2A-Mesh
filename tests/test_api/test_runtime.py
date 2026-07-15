"""Tests for agent runtime endpoints — deploy, stop, status, logs."""

import pytest
from httpx import AsyncClient

from a2a_mesh.orchestrator import registry

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def auth_token(client: AsyncClient) -> str:
    resp = await client.post("/v1/auth/register", json={
        "company_name": "Runtime Co",
        "namespace": "runtimeco",
        "email": "admin@runtimeco.com",
        "password": "secret123",
    })
    return resp.json()["access_token"]


@pytest.fixture
async def agent_id(client: AsyncClient, auth_token: str) -> str:
    resp = await client.post("/v1/agents", json={
        "name": "test-agent",
        "display_name": "Test Agent",
        "description": "Runtime test agent",
    }, headers={"Authorization": f"Bearer {auth_token}"})
    return resp.json()["id"]


# ── Deploy ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deploy_agent(client: AsyncClient, auth_token: str, agent_id: str) -> None:
    resp = await client.post(
        f"/v1/agents/{agent_id}/deploy",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["endpoint_url"] == f"http://localhost:8000/a2a/{agent_id}/"
    registry.unregister(agent_id)


@pytest.mark.asyncio
async def test_deploy_agent_twice_returns_409(
    client: AsyncClient, auth_token: str, agent_id: str
) -> None:
    await client.post(
        f"/v1/agents/{agent_id}/deploy",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    resp = await client.post(
        f"/v1/agents/{agent_id}/deploy",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 409
    registry.unregister(agent_id)


@pytest.mark.asyncio
async def test_deploy_agent_not_found(client: AsyncClient, auth_token: str) -> None:
    resp = await client.post(
        "/v1/agents/agt_doesnotexist/deploy",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_deploy_requires_auth(client: AsyncClient, agent_id: str) -> None:
    resp = await client.post(f"/v1/agents/{agent_id}/deploy")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_deploy_rejects_unreachable_mcp_server(client: AsyncClient, auth_token: str) -> None:
    """A misconfigured mcp_servers URL fails deploy, not the first message the agent gets."""
    create_resp = await client.post(
        "/v1/agents",
        json={
            "name": "mcp-agent",
            "display_name": "MCP Agent",
            "config": {"mcp_servers": ["http://127.0.0.1:1/mcp"]},
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    agent_id_ = create_resp.json()["id"]

    resp = await client.post(
        f"/v1/agents/{agent_id_}/deploy",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"
    assert registry.get(agent_id_) is None


@pytest.mark.asyncio
async def test_deploy_accepts_reachable_mcp_server(
    client: AsyncClient, auth_token: str, mock_mcp_server: str
) -> None:
    create_resp = await client.post(
        "/v1/agents",
        json={
            "name": "mcp-agent-ok",
            "display_name": "MCP Agent OK",
            "config": {"mcp_servers": [mock_mcp_server]},
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    agent_id_ = create_resp.json()["id"]

    resp = await client.post(
        f"/v1/agents/{agent_id_}/deploy",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
    registry.unregister(agent_id_)


# ── Stop ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stop_agent(client: AsyncClient, auth_token: str, agent_id: str) -> None:
    await client.post(
        f"/v1/agents/{agent_id}/deploy",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    resp = await client.post(
        f"/v1/agents/{agent_id}/stop",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"
    assert registry.get(agent_id) is None


@pytest.mark.asyncio
async def test_stop_agent_not_running_is_idempotent(
    client: AsyncClient, auth_token: str, agent_id: str
) -> None:
    resp = await client.post(
        f"/v1/agents/{agent_id}/stop",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"


# ── Status ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_status_before_deploy(
    client: AsyncClient, auth_token: str, agent_id: str
) -> None:
    resp = await client.get(
        f"/v1/agents/{agent_id}/status",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"


@pytest.mark.asyncio
async def test_status_after_deploy(
    client: AsyncClient, auth_token: str, agent_id: str
) -> None:
    await client.post(
        f"/v1/agents/{agent_id}/deploy",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    resp = await client.get(
        f"/v1/agents/{agent_id}/status",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
    registry.unregister(agent_id)


# ── Logs ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logs_returns_empty_list(
    client: AsyncClient, auth_token: str, agent_id: str
) -> None:
    resp = await client.get(
        f"/v1/agents/{agent_id}/logs",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_not_deployed_is_unhealthy(
    client: AsyncClient, auth_token: str, agent_id: str
) -> None:
    resp = await client.get(
        f"/v1/agents/{agent_id}/health",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["healthy"] is False
    assert data["latency_ms"] is None


@pytest.mark.asyncio
async def test_health_deployed_is_healthy(
    client: AsyncClient, auth_token: str, agent_id: str
) -> None:
    await client.post(
        f"/v1/agents/{agent_id}/deploy",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    resp = await client.get(
        f"/v1/agents/{agent_id}/health",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["healthy"] is True
    assert data["latency_ms"] is not None
    assert data["latency_ms"] >= 0
    registry.unregister(agent_id)


# ── Restart ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_restart_stopped_agent(
    client: AsyncClient, auth_token: str, agent_id: str
) -> None:
    resp = await client.post(
        f"/v1/agents/{agent_id}/restart",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
    registry.unregister(agent_id)


@pytest.mark.asyncio
async def test_restart_running_agent_replaces_instance(
    client: AsyncClient, auth_token: str, agent_id: str
) -> None:
    await client.post(
        f"/v1/agents/{agent_id}/deploy",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    first_instance = registry.get(agent_id)

    await client.post(
        f"/v1/agents/{agent_id}/restart",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    second_instance = registry.get(agent_id)

    assert second_instance is not None
    assert second_instance is not first_instance
    registry.unregister(agent_id)
