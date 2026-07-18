"""Tests for pipeline CRUD and execution endpoints."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from a2a_mesh.agents.coder import build_coder_config
from a2a_mesh.agents.reviewer import build_reviewer_config
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


# ── loop_until: Coder ↔ Reviewer ──────────────────────────────────────────────

LOGIN_V1 = (
    '_USERS = {"alice": "hunter2"}\n\n'
    "def login(username, password):\n"
    "    return _USERS.get(username) == password\n"
)
LOGIN_V2 = (
    'import hashlib\n\n_USERS = {"alice": hashlib.sha256(b"hunter2").hexdigest()}\n\n'
    "def login(username, password):\n"
    "    return _USERS.get(username) == hashlib.sha256(password.encode()).hexdigest()\n"
)
LOGIN_TEST = (
    "from login import login\n\n"
    "def test_login_success():\n"
    '    assert login("alice", "hunter2") is True\n'
)


def _tool_call(call_id: str, name: str, arguments: dict) -> SimpleNamespace:  # type: ignore[type-arg]
    function = SimpleNamespace(name=name, arguments=json.dumps(arguments))
    tool_call = SimpleNamespace(id=call_id, function=function)
    message = SimpleNamespace(content=None, tool_calls=[tool_call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _final(content: str) -> SimpleNamespace:  # type: ignore[type-arg]
    message = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _coder_run_script(call_offset: int, code: str) -> list[SimpleNamespace]:  # type: ignore[type-arg]
    return [
        _tool_call(f"call_{call_offset}_1", "file_write", {"path": "login.py", "content": code}),
        _tool_call(f"call_{call_offset}_2", "file_write", {"path": "test_login.py", "content": LOGIN_TEST}),
        _tool_call(f"call_{call_offset}_3", "run_tests", {}),
        _final(f"Done. login.py:\n{code}"),
    ]


@pytest.mark.asyncio
async def test_run_pipeline_coder_reviewer_loop_until_approved(
    client: AsyncClient, auth_token: str, mock_llm
) -> None:  # type: ignore[no-untyped-def]
    """Reviewer rejects the first draft, Coder revises, Reviewer approves — loop_until exits."""
    headers = {"Authorization": f"Bearer {auth_token}"}

    coder_cfg = build_coder_config()
    resp = await client.post("/v1/agents", json={
        "name": coder_cfg.name,
        "display_name": coder_cfg.display_name,
        "description": coder_cfg.description,
        "system_prompt": coder_cfg.system_prompt,
        "config": {"tools": coder_cfg.tools},
    }, headers=headers)
    coder_id = resp.json()["id"]

    reviewer_cfg = build_reviewer_config()
    resp = await client.post("/v1/agents", json={
        "name": reviewer_cfg.name,
        "display_name": reviewer_cfg.display_name,
        "description": reviewer_cfg.description,
        "system_prompt": reviewer_cfg.system_prompt,
    }, headers=headers)
    reviewer_id = resp.json()["id"]

    resp = await client.post("/v1/pipelines", json={
        "name": "coder-reviewer-loop",
        "steps": [
            {"agent_id": coder_id, "name": "coder"},
            {
                "agent_id": reviewer_id,
                "name": "reviewer",
                "loop_until": {"field": "approved", "equals": True},
                "max_iterations": 3,
            },
        ],
    }, headers=headers)
    pip_id = resp.json()["id"]

    await client.post(f"/v1/agents/{coder_id}/deploy", headers=headers)
    await client.post(f"/v1/agents/{reviewer_id}/deploy", headers=headers)

    coder_script = _coder_run_script(1, LOGIN_V1) + _coder_run_script(2, LOGIN_V2)
    calls: list[dict] = []  # type: ignore[type-arg]

    async def fake_acompletion(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)  # type: ignore[arg-type]
        return coder_script[len(calls) - 1]

    mock_llm.side_effect = [
        '{"approved": false, "feedback": "Passwords are compared in plaintext."}',
        '{"approved": true, "feedback": "Now uses hashed comparison."}',
    ]

    try:
        with patch("a2a_mesh.llm.dispatch.litellm.acompletion", side_effect=fake_acompletion):
            resp = await client.post(f"/v1/pipelines/{pip_id}/run",
                                     json={"input": "add a login function"},
                                     headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"

        final = json.loads(json.loads(data["output"])["text"])
        assert final["approved"] is True
        assert len(coder_script) == len(calls)  # Coder ran exactly twice (4 calls each)
    finally:
        registry.unregister(coder_id)
        registry.unregister(reviewer_id)


@pytest.mark.asyncio
async def test_run_pipeline_loop_until_fails_after_max_iterations(
    client: AsyncClient, auth_token: str, mock_llm
) -> None:  # type: ignore[no-untyped-def]
    """Reviewer never approves — pipeline fails once max_iterations is exhausted."""
    headers = {"Authorization": f"Bearer {auth_token}"}

    coder_cfg = build_coder_config()
    resp = await client.post("/v1/agents", json={
        "name": coder_cfg.name,
        "display_name": coder_cfg.display_name,
        "description": coder_cfg.description,
        "system_prompt": coder_cfg.system_prompt,
        "config": {"tools": coder_cfg.tools},
    }, headers=headers)
    coder_id = resp.json()["id"]

    reviewer_cfg = build_reviewer_config()
    resp = await client.post("/v1/agents", json={
        "name": reviewer_cfg.name,
        "display_name": reviewer_cfg.display_name,
        "description": reviewer_cfg.description,
        "system_prompt": reviewer_cfg.system_prompt,
    }, headers=headers)
    reviewer_id = resp.json()["id"]

    resp = await client.post("/v1/pipelines", json={
        "name": "coder-reviewer-loop-fail",
        "steps": [
            {"agent_id": coder_id, "name": "coder"},
            {
                "agent_id": reviewer_id,
                "name": "reviewer",
                "loop_until": {"field": "approved", "equals": True},
                "max_iterations": 2,
            },
        ],
    }, headers=headers)
    pip_id = resp.json()["id"]

    await client.post(f"/v1/agents/{coder_id}/deploy", headers=headers)
    await client.post(f"/v1/agents/{reviewer_id}/deploy", headers=headers)

    coder_script = _coder_run_script(1, LOGIN_V1) + _coder_run_script(2, LOGIN_V1)
    calls: list[dict] = []  # type: ignore[type-arg]

    async def fake_acompletion(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)  # type: ignore[arg-type]
        return coder_script[len(calls) - 1]

    mock_llm.return_value = '{"approved": false, "feedback": "Still plaintext."}'

    try:
        with patch("a2a_mesh.llm.dispatch.litellm.acompletion", side_effect=fake_acompletion):
            resp = await client.post(f"/v1/pipelines/{pip_id}/run",
                                     json={"input": "add a login function"},
                                     headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert "loop_until" in data["error"]
    finally:
        registry.unregister(coder_id)
        registry.unregister(reviewer_id)
