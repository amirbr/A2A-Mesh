"""Pipeline CRUD and run endpoints."""

import json
import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from a2a_mesh.api.v1.auth import get_current_user
from a2a_mesh.core.errors import ForbiddenError, NotFoundError, ValidationError
from a2a_mesh.db.models.pipeline import Pipeline, PipelineRun
from a2a_mesh.db.session import AsyncSessionLocal
from a2a_mesh.orchestrator.engine import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/pipelines", tags=["pipelines"])

Claims = Annotated[dict, Depends(get_current_user)]  # type: ignore[type-arg]


# ── Schemas ───────────────────────────────────────────────────────────────────

class StepConfig(BaseModel):
    agent_id: str
    name: str
    loop_until: dict[str, Any] | None = None
    max_iterations: int | None = None


class PipelineCreate(BaseModel):
    name: str
    description: str = ""
    steps: list[StepConfig] = []


class PipelineUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    steps: list[StepConfig] | None = None


class PipelineResponse(BaseModel):
    id: str
    company_id: str
    name: str
    description: str
    steps: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class RunRequest(BaseModel):
    input: str


class RunResponse(BaseModel):
    id: str
    pipeline_id: str
    status: str
    input: str
    output: str | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_response(p: Pipeline) -> PipelineResponse:
    return PipelineResponse(
        id=p.id,
        company_id=p.company_id,
        name=p.name,
        description=p.description,
        steps=p.get_steps(),
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _run_to_response(r: PipelineRun) -> RunResponse:
    return RunResponse(
        id=r.id,
        pipeline_id=r.pipeline_id,
        status=r.status,
        input=r.input,
        output=r.output,
        error=r.error,
        started_at=r.started_at,
        completed_at=r.completed_at,
    )


async def _get_owned_pipeline(pipeline_id: str, company_id: str) -> Pipeline:
    async with AsyncSessionLocal() as session:
        pipeline = await session.get(Pipeline, pipeline_id)
    if not pipeline:
        raise NotFoundError("Pipeline")
    if pipeline.company_id != company_id:
        raise ForbiddenError()
    return pipeline


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", status_code=201, response_model=PipelineResponse)
async def create_pipeline(body: PipelineCreate, claims: Claims) -> PipelineResponse:
    """Create a new pipeline."""
    pipeline = Pipeline(
        company_id=claims["company_id"],
        name=body.name,
        description=body.description,
        steps=json.dumps([s.model_dump() for s in body.steps]),
    )
    async with AsyncSessionLocal() as session:
        async with session.begin():
            session.add(pipeline)
    logger.info("Created pipeline %s for company %s", pipeline.id, pipeline.company_id)
    return _to_response(pipeline)


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines(claims: Claims) -> list[PipelineResponse]:
    """List all pipelines for the current company."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Pipeline).where(Pipeline.company_id == claims["company_id"])
        )
        pipelines = result.scalars().all()
    return [_to_response(p) for p in pipelines]


@router.get("/{id}", response_model=PipelineResponse)
async def get_pipeline(id: str, claims: Claims) -> PipelineResponse:
    """Get a single pipeline."""
    pipeline = await _get_owned_pipeline(id, claims["company_id"])
    return _to_response(pipeline)


@router.patch("/{id}", response_model=PipelineResponse)
async def update_pipeline(id: str, body: PipelineUpdate, claims: Claims) -> PipelineResponse:
    """Update a pipeline's name, description, or steps."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            pipeline = await session.get(Pipeline, id)
            if not pipeline:
                raise NotFoundError("Pipeline")
            if pipeline.company_id != claims["company_id"]:
                raise ForbiddenError()
            if body.name is not None:
                pipeline.name = body.name
            if body.description is not None:
                pipeline.description = body.description
            if body.steps is not None:
                pipeline.set_steps([s.model_dump() for s in body.steps])
    return _to_response(pipeline)


@router.delete("/{id}", status_code=204)
async def delete_pipeline(id: str, claims: Claims) -> None:
    """Delete a pipeline."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            pipeline = await session.get(Pipeline, id)
            if not pipeline:
                raise NotFoundError("Pipeline")
            if pipeline.company_id != claims["company_id"]:
                raise ForbiddenError()
            await session.delete(pipeline)


@router.post("/{id}/run", response_model=RunResponse)
async def run_pipeline_endpoint(id: str, body: RunRequest, claims: Claims) -> RunResponse:
    """Execute a pipeline sequentially and return the result."""
    pipeline = await _get_owned_pipeline(id, claims["company_id"])
    steps = pipeline.get_steps()
    if not steps:
        raise ValidationError("Pipeline has no steps")

    pipeline_run = await run_pipeline(pipeline_id=id, steps=steps, input_text=body.input)
    return _run_to_response(pipeline_run)


@router.get("/{id}/runs/{run_id}", response_model=RunResponse)
async def get_run(id: str, run_id: str, claims: Claims) -> RunResponse:
    """Get the status and output of a pipeline run."""
    await _get_owned_pipeline(id, claims["company_id"])
    async with AsyncSessionLocal() as session:
        pipeline_run = await session.get(PipelineRun, run_id)
    if not pipeline_run or pipeline_run.pipeline_id != id:
        raise NotFoundError("PipelineRun")
    return _run_to_response(pipeline_run)
