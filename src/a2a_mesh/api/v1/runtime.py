"""Agent runtime endpoints — deploy, stop, status, logs."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from a2a_mesh.agents.base import AgentConfig, SkillConfig
from a2a_mesh.agents.generic import GenericAgent
from a2a_mesh.api.v1.auth import get_current_user
from a2a_mesh.core.errors import ConflictError, ForbiddenError, NotFoundError
from a2a_mesh.db.models.agent import Agent
from a2a_mesh.db.session import AsyncSessionLocal
from a2a_mesh.orchestrator import registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/agents", tags=["runtime"])

Claims = Annotated[dict, Depends(get_current_user)]  # type: ignore[type-arg]

APP_BASE_URL = "http://localhost:8000"


# ── Schemas ──────────────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    id: str
    name: str
    status: str
    endpoint_url: str | None


class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_owned_agent(agent_id: str, company_id: str) -> Agent:
    async with AsyncSessionLocal() as session:
        agent = await session.get(Agent, agent_id)
    if not agent:
        raise NotFoundError("Agent")
    if agent.company_id != company_id:
        raise ForbiddenError()
    return agent


def _build_agent_instance(agent: Agent) -> GenericAgent:
    raw_config = json.loads(agent.config) if agent.config else {}
    config = AgentConfig(
        name=agent.name,
        display_name=agent.display_name,
        description=agent.description,
        version=agent.version,
        system_prompt=raw_config.get("system_prompt", ""),
        model=raw_config.get("model", "claude-opus-4-8"),
        skills=[
            SkillConfig(**s) for s in raw_config.get("skills", [])
        ],
    )
    return GenericAgent(config)


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/{id}/deploy", response_model=StatusResponse)
async def deploy_agent(id: str, claims: Claims) -> StatusResponse:
    """Deploy an agent — instantiate it and register for A2A calls."""
    agent = await _get_owned_agent(id, claims["company_id"])

    if registry.get(id):
        raise ConflictError(f"Agent '{agent.name}' is already running")

    instance = _build_agent_instance(agent)
    await instance.on_start()
    registry.register(id, instance)

    endpoint_url = f"{APP_BASE_URL}/a2a/{id}/"
    async with AsyncSessionLocal() as session:
        async with session.begin():
            db_agent = await session.get(Agent, id)
            if db_agent:
                db_agent.status = "running"
                db_agent.endpoint_url = endpoint_url

    logger.info("Deployed agent %s at %s", id, endpoint_url)
    return StatusResponse(id=id, name=agent.name, status="running", endpoint_url=endpoint_url)


@router.post("/{id}/stop", response_model=StatusResponse)
async def stop_agent(id: str, claims: Claims) -> StatusResponse:
    """Stop a running agent."""
    agent = await _get_owned_agent(id, claims["company_id"])

    instance = registry.get(id)
    if instance:
        await instance.on_stop()
        registry.unregister(id)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            db_agent = await session.get(Agent, id)
            if db_agent:
                db_agent.status = "stopped"
                db_agent.endpoint_url = None

    return StatusResponse(id=id, name=agent.name, status="stopped", endpoint_url=None)


@router.get("/{id}/status", response_model=StatusResponse)
async def agent_status(id: str, claims: Claims) -> StatusResponse:
    """Return the current status of an agent."""
    agent = await _get_owned_agent(id, claims["company_id"])
    return StatusResponse(
        id=id,
        name=agent.name,
        status=agent.status,
        endpoint_url=agent.endpoint_url,
    )


@router.get("/{id}/logs", response_model=list[LogEntry])
async def agent_logs(id: str, claims: Claims) -> list[LogEntry]:
    """Return recent logs for an agent (stub — structured logging in Week 8)."""
    await _get_owned_agent(id, claims["company_id"])
    return []
