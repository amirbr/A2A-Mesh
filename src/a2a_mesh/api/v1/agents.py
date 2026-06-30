"""Agent CRUD routes — /v1/agents/*."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from a2a_mesh.api.v1.auth import get_current_user
from a2a_mesh.core.errors import ConflictError, ForbiddenError, NotFoundError
from a2a_mesh.core.ids import agent_id
from a2a_mesh.db.models.agent import Agent
from a2a_mesh.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/agents", tags=["agents"])

Claims = Annotated[dict, Depends(get_current_user)]  # type: ignore[type-arg]


# ── Schemas ──────────────────────────────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    name: str
    display_name: str
    description: str = ""
    version: str = "1.0.0"
    visibility: str = "private"
    runtime: str = "managed"
    config: dict = {}  # type: ignore[type-arg]


class UpdateAgentRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    version: str | None = None
    visibility: str | None = None
    config: dict | None = None  # type: ignore[type-arg]


class AgentResponse(BaseModel):
    id: str
    company_id: str
    name: str
    display_name: str
    description: str
    version: str
    status: str
    visibility: str
    runtime: str
    config: dict  # type: ignore[type-arg]
    endpoint_url: str | None
    created_at: str
    updated_at: str


def _to_response(agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        company_id=agent.company_id,
        name=agent.name,
        display_name=agent.display_name,
        description=agent.description,
        version=agent.version,
        status=agent.status,
        visibility=agent.visibility,
        runtime=agent.runtime,
        config=json.loads(agent.config),
        endpoint_url=agent.endpoint_url,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat(),
    )


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(body: CreateAgentRequest, claims: Claims) -> AgentResponse:
    """Register a new agent for the current company."""
    company_id = claims["company_id"]

    async with AsyncSessionLocal() as session:
        async with session.begin():
            existing = await session.execute(
                select(Agent).where(Agent.company_id == company_id, Agent.name == body.name)
            )
            if existing.scalar_one_or_none():
                raise ConflictError(f"Agent '{body.name}' already exists in your company")

            agent = Agent(
                id=agent_id(),
                company_id=company_id,
                name=body.name,
                display_name=body.display_name,
                description=body.description,
                version=body.version,
                visibility=body.visibility,
                runtime=body.runtime,
                config=json.dumps(body.config),
                status="stopped",
            )
            session.add(agent)
            await session.flush()
            response = _to_response(agent)

    logger.info("Created agent %s for company %s", agent.id, company_id)
    return response


@router.get("", response_model=list[AgentResponse])
async def list_agents(claims: Claims) -> list[AgentResponse]:
    """List all agents for the current company."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Agent).where(Agent.company_id == claims["company_id"])
        )
        agents = result.scalars().all()
    return [_to_response(a) for a in agents]


@router.get("/{id}", response_model=AgentResponse)
async def get_agent(id: str, claims: Claims) -> AgentResponse:
    """Get a single agent by ID."""
    async with AsyncSessionLocal() as session:
        agent = await session.get(Agent, id)

    if not agent:
        raise NotFoundError("Agent")
    if agent.company_id != claims["company_id"]:
        raise ForbiddenError()
    return _to_response(agent)


@router.patch("/{id}", response_model=AgentResponse)
async def update_agent(id: str, body: UpdateAgentRequest, claims: Claims) -> AgentResponse:
    """Update mutable fields on an agent."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            agent = await session.get(Agent, id)
            if not agent:
                raise NotFoundError("Agent")
            if agent.company_id != claims["company_id"]:
                raise ForbiddenError()

            if body.display_name is not None:
                agent.display_name = body.display_name
            if body.description is not None:
                agent.description = body.description
            if body.version is not None:
                agent.version = body.version
            if body.visibility is not None:
                agent.visibility = body.visibility
            if body.config is not None:
                agent.config = json.dumps(body.config)

            await session.flush()
            response = _to_response(agent)

    return response


@router.delete("/{id}", status_code=204)
async def delete_agent(id: str, claims: Claims) -> None:
    """Delete an agent."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            agent = await session.get(Agent, id)
            if not agent:
                raise NotFoundError("Agent")
            if agent.company_id != claims["company_id"]:
                raise ForbiddenError()
            await session.delete(agent)
