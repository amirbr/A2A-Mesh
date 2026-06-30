"""Tests for /v1/agents/* endpoints."""

import pytest
from httpx import AsyncClient

REGISTER_BODY = {
    "company_name": "Agent Test Corp",
    "namespace": "agenttest",
    "email": "admin@agenttest.com",
    "password": "strongpassword123",
}

CREATE_AGENT_BODY = {
    "name": "my-coder",
    "display_name": "My Coder",
    "description": "A coding agent",
    "visibility": "private",
}


async def _auth_headers(client: AsyncClient) -> dict:
    r = await client.post("/v1/auth/register", json=REGISTER_BODY)
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestCreateAgent:
    async def test_create_agent_returns_201(self, client: AsyncClient) -> None:
        headers = await _auth_headers(client)
        response = await client.post("/v1/agents", json=CREATE_AGENT_BODY, headers=headers)
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "my-coder"
        assert body["status"] == "stopped"
        assert body["id"].startswith("agt_")

    async def test_create_agent_duplicate_name_fails(self, client: AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post("/v1/agents", json=CREATE_AGENT_BODY, headers=headers)
        response = await client.post("/v1/agents", json=CREATE_AGENT_BODY, headers=headers)
        assert response.status_code == 409

    async def test_create_agent_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post("/v1/agents", json=CREATE_AGENT_BODY)
        assert response.status_code == 401


class TestListAgents:
    async def test_list_agents_returns_empty(self, client: AsyncClient) -> None:
        headers = await _auth_headers(client)
        response = await client.get("/v1/agents", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_agents_returns_created(self, client: AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post("/v1/agents", json=CREATE_AGENT_BODY, headers=headers)
        await client.post("/v1/agents", json={**CREATE_AGENT_BODY, "name": "my-reviewer"}, headers=headers)
        response = await client.get("/v1/agents", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_list_agents_scoped_to_company(self, client: AsyncClient) -> None:
        headers_a = await _auth_headers(client)
        headers_b = {"Authorization": "Bearer " + (
            await client.post("/v1/auth/register", json={**REGISTER_BODY, "namespace": "other", "email": "b@other.com"})
        ).json()["access_token"]}
        await client.post("/v1/agents", json=CREATE_AGENT_BODY, headers=headers_a)
        response = await client.get("/v1/agents", headers=headers_b)
        assert response.json() == []


class TestGetAgent:
    async def test_get_agent_returns_agent(self, client: AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = (await client.post("/v1/agents", json=CREATE_AGENT_BODY, headers=headers)).json()
        response = await client.get(f"/v1/agents/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_get_agent_not_found(self, client: AsyncClient) -> None:
        headers = await _auth_headers(client)
        response = await client.get("/v1/agents/agt_doesnotexist", headers=headers)
        assert response.status_code == 404

    async def test_get_agent_wrong_company_forbidden(self, client: AsyncClient) -> None:
        headers_a = await _auth_headers(client)
        headers_b = {"Authorization": "Bearer " + (
            await client.post("/v1/auth/register", json={**REGISTER_BODY, "namespace": "other2", "email": "b@other2.com"})
        ).json()["access_token"]}
        created = (await client.post("/v1/agents", json=CREATE_AGENT_BODY, headers=headers_a)).json()
        response = await client.get(f"/v1/agents/{created['id']}", headers=headers_b)
        assert response.status_code == 403


class TestUpdateAgent:
    async def test_update_agent_display_name(self, client: AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = (await client.post("/v1/agents", json=CREATE_AGENT_BODY, headers=headers)).json()
        response = await client.patch(
            f"/v1/agents/{created['id']}",
            json={"display_name": "Updated Name"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Updated Name"

    async def test_update_agent_not_found(self, client: AsyncClient) -> None:
        headers = await _auth_headers(client)
        response = await client.patch("/v1/agents/agt_doesnotexist", json={"display_name": "x"}, headers=headers)
        assert response.status_code == 404


class TestDeleteAgent:
    async def test_delete_agent_returns_204(self, client: AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = (await client.post("/v1/agents", json=CREATE_AGENT_BODY, headers=headers)).json()
        response = await client.delete(f"/v1/agents/{created['id']}", headers=headers)
        assert response.status_code == 204

    async def test_delete_agent_then_not_found(self, client: AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = (await client.post("/v1/agents", json=CREATE_AGENT_BODY, headers=headers)).json()
        await client.delete(f"/v1/agents/{created['id']}", headers=headers)
        response = await client.get(f"/v1/agents/{created['id']}", headers=headers)
        assert response.status_code == 404
