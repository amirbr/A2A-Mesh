"""Tests for pipeline CRUD and execution endpoints."""

import pytest
from httpx import AsyncClient

from a2a_mesh.orchestrator import registry


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def auth_token(client: AsyncClient) -> str:
    resp = await client.post("/v1/auth/register", json={
        "company_name": "Pipeline Co",
        "namespace": "pipelineco",
        "email": "admin@pipelineco.com",
        "password": "secret123",
    })
    return resp.json()["access_token"]


@pytest.fixture
async def agent_id(client: AsyncClient, auth_token: str) -> str:
    resp = await client.post("/v1/agents", json={
        "name": "step-agent",
        "display_name": "Step Agent",
        "description": "Pipeline step agent",
    }, headers={"Authorization": f"Bearer {auth_token}"})
    return resp.json()["id"]


@pytest.fixture
async def pipeline_id(client: AsyncClient, auth_token: str, agent_id: str) -> str:
    resp = await client.post("/v1/pipelines", json={
        "name": "my-pipeline",
        "description": "Test pipeline",
        "steps": [{"agent_id": agent_id, "name": "step-one"}],
    }, headers={"Authorization": f"Bearer {auth_token}"})
    return resp.json()["id"]


# ── CRUD ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_pipeline_returns_201(client: AsyncClient, auth_token: str, agent_id: str) -> None:
    resp = await client.post("/v1/pipelines", json={
        "name": "dev-pipeline",
        "description": "Coder → Reviewer",
        "steps": [{"agent_id": agent_id, "name": "coder"}],
    }, headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "dev-pipeline"
    assert data["id"].startswith("pip_")
    assert len(data["steps"]) == 1


@pytest.mark.asyncio
async def test_list_pipelines(client: AsyncClient, auth_token: str, pipeline_id: str) -> None:
    resp = await client.get("/v1/pipelines", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert any(p["id"] == pipeline_id for p in resp.json())


@pytest.mark.asyncio
async def test_get_pipeline(client: AsyncClient, auth_token: str, pipeline_id: str) -> None:
    resp = await client.get(f"/v1/pipelines/{pipeline_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == pipeline_id


@pytest.mark.asyncio
async def test_get_pipeline_not_found(client: AsyncClient, auth_token: str) -> None:
    resp = await client.get("/v1/pipelines/pip_doesnotexist", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_pipeline(client: AsyncClient, auth_token: str, pipeline_id: str) -> None:
    resp = await client.patch(f"/v1/pipelines/{pipeline_id}", json={
        "name": "updated-pipeline",
        "description": "New description",
    }, headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "updated-pipeline"


@pytest.mark.asyncio
async def test_delete_pipeline(client: AsyncClient, auth_token: str, pipeline_id: str) -> None:
    resp = await client.delete(f"/v1/pipelines/{pipeline_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 204

    resp = await client.get(f"/v1/pipelines/{pipeline_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pipeline_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/v1/pipelines")
    assert resp.status_code == 401


# ── Execution ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_pipeline_success(
    client: AsyncClient, auth_token: str, agent_id: str, pipeline_id: str
) -> None:
    await client.post(f"/v1/agents/{agent_id}/deploy", headers={"Authorization": f"Bearer {auth_token}"})

    resp = await client.post(f"/v1/pipelines/{pipeline_id}/run",
                             json={"input": "write a hello world function"},
                             headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["output"] is not None
    registry.unregister(agent_id)


@pytest.mark.asyncio
async def test_run_pipeline_agent_not_deployed(
    client: AsyncClient, auth_token: str, pipeline_id: str
) -> None:
    resp = await client.post(f"/v1/pipelines/{pipeline_id}/run",
                             json={"input": "hello"},
                             headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert "not deployed" in data["error"]


@pytest.mark.asyncio
async def test_run_pipeline_no_steps(client: AsyncClient, auth_token: str) -> None:
    resp = await client.post("/v1/pipelines", json={
        "name": "empty-pipeline",
        "steps": [],
    }, headers={"Authorization": f"Bearer {auth_token}"})
    empty_id = resp.json()["id"]

    resp = await client.post(f"/v1/pipelines/{empty_id}/run",
                             json={"input": "hello"},
                             headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_run_status(
    client: AsyncClient, auth_token: str, agent_id: str, pipeline_id: str
) -> None:
    await client.post(f"/v1/agents/{agent_id}/deploy", headers={"Authorization": f"Bearer {auth_token}"})

    run_resp = await client.post(f"/v1/pipelines/{pipeline_id}/run",
                                 json={"input": "test input"},
                                 headers={"Authorization": f"Bearer {auth_token}"})
    run_id = run_resp.json()["id"]

    resp = await client.get(f"/v1/pipelines/{pipeline_id}/runs/{run_id}",
                            headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id
    registry.unregister(agent_id)


@pytest.mark.asyncio
async def test_run_two_step_pipeline(
    client: AsyncClient, auth_token: str, agent_id: str
) -> None:
    resp = await client.post("/v1/agents", json={
        "name": "second-agent",
        "display_name": "Second Agent",
        "description": "Second step",
    }, headers={"Authorization": f"Bearer {auth_token}"})
    agent2_id = resp.json()["id"]

    resp = await client.post("/v1/pipelines", json={
        "name": "two-step",
        "steps": [
            {"agent_id": agent_id, "name": "step-one"},
            {"agent_id": agent2_id, "name": "step-two"},
        ],
    }, headers={"Authorization": f"Bearer {auth_token}"})
    pip_id = resp.json()["id"]

    await client.post(f"/v1/agents/{agent_id}/deploy", headers={"Authorization": f"Bearer {auth_token}"})
    await client.post(f"/v1/agents/{agent2_id}/deploy", headers={"Authorization": f"Bearer {auth_token}"})

    resp = await client.post(f"/v1/pipelines/{pip_id}/run",
                             json={"input": "start"},
                             headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    registry.unregister(agent_id)
    registry.unregister(agent2_id)
