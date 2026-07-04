"""Tests for the dynamic A2A dispatch router."""

import pytest
from httpx import AsyncClient

from a2a_mesh.orchestrator import registry

SEND_MSG = {
    "jsonrpc": "2.0",
    "id": "1",
    "method": "SendMessage",
    "params": {
        "message": {
            "messageId": "msg-001",
            "role": "ROLE_USER",
            "parts": [{"text": "hello agent"}],
        }
    },
}

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def token_and_agent(client: AsyncClient) -> tuple[str, str]:
    reg = await client.post("/v1/auth/register", json={
        "company_name": "Dispatch Co",
        "namespace": "dispatchco",
        "email": "admin@dispatchco.com",
        "password": "secret123",
    })
    token = reg.json()["access_token"]
    ag = await client.post("/v1/agents", json={
        "name": "dispatch-agent",
        "display_name": "Dispatch Agent",
        "description": "Test dispatch agent",
    }, headers={"Authorization": f"Bearer {token}"})
    return token, ag.json()["id"]


# ── Dispatch: not deployed ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dispatch_not_deployed_returns_404(client: AsyncClient, token_and_agent: tuple) -> None:
    _, agent_id = token_and_agent
    resp = await client.post(f"/a2a/{agent_id}/", json=SEND_MSG,
                             headers={"A2A-Version": "1.0"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == -32001


# ── Dispatch: deployed ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dispatch_deployed_returns_response(client: AsyncClient, token_and_agent: tuple) -> None:
    token, agent_id = token_and_agent
    await client.post(f"/v1/agents/{agent_id}/deploy",
                      headers={"Authorization": f"Bearer {token}"})

    resp = await client.post(f"/a2a/{agent_id}/", json=SEND_MSG,
                             headers={"A2A-Version": "1.0"})
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert "message" in data["result"]
    parts = data["result"]["message"]["parts"]
    assert any(p.get("text") for p in parts)
    registry.unregister(agent_id)


@pytest.mark.asyncio
async def test_dispatch_unsupported_method(client: AsyncClient, token_and_agent: tuple) -> None:
    token, agent_id = token_and_agent
    await client.post(f"/v1/agents/{agent_id}/deploy",
                      headers={"Authorization": f"Bearer {token}"})

    resp = await client.post(f"/a2a/{agent_id}/", json={
        "jsonrpc": "2.0", "id": "1", "method": "GetTask", "params": {},
    })
    assert resp.status_code == 200
    assert resp.json()["error"]["code"] == -32601
    registry.unregister(agent_id)


# ── Agent card ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_card_not_deployed_returns_404(client: AsyncClient, token_and_agent: tuple) -> None:
    _, agent_id = token_and_agent
    resp = await client.get(f"/a2a/{agent_id}/.well-known/agent-card.json")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_agent_card_deployed_returns_card(client: AsyncClient, token_and_agent: tuple) -> None:
    token, agent_id = token_and_agent
    await client.post(f"/v1/agents/{agent_id}/deploy",
                      headers={"Authorization": f"Bearer {token}"})

    resp = await client.get(f"/a2a/{agent_id}/.well-known/agent-card.json")
    assert resp.status_code == 200
    card = resp.json()
    assert card["name"] == "dispatch-agent"
    registry.unregister(agent_id)
