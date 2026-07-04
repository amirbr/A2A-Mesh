"""Pipeline execution engine — runs steps sequentially, pipes output to next step."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from a2a_mesh.api.a2a.dispatch import _build_context, _parse_message
from a2a_mesh.core.errors import ValidationError
from a2a_mesh.db.models.pipeline import PipelineRun
from a2a_mesh.db.session import AsyncSessionLocal
from a2a_mesh.orchestrator import registry

logger = logging.getLogger(__name__)


def _make_context(text: str) -> Any:
    """Build a minimal RequestContext from a text string."""
    import secrets
    return _build_context(_parse_message({"message": {
        "messageId": f"pip_{secrets.token_hex(6)}",
        "role": "ROLE_USER",
        "parts": [{"text": text}],
    }}))


async def run_pipeline(
    pipeline_id: str,
    steps: list[dict[str, Any]],
    input_text: str,
) -> PipelineRun:
    """Execute pipeline steps sequentially.

    Each step's output becomes the next step's input.

    Args:
        pipeline_id: DB id of the pipeline being run.
        steps: Ordered list of {"agent_id": ..., "name": ...} dicts.
        input_text: The initial user input fed into step 0.

    Returns:
        The completed (or failed) PipelineRun record.
    """
    pipeline_run = PipelineRun(
        pipeline_id=pipeline_id,
        status="running",
        input=json.dumps({"text": input_text}),
        started_at=datetime.now(timezone.utc),
    )
    async with AsyncSessionLocal() as session:
        async with session.begin():
            session.add(pipeline_run)

    current_input = input_text
    try:
        for i, step in enumerate(steps):
            agent_id = step.get("agent_id", "")
            step_name = step.get("name", agent_id)
            agent = registry.get(agent_id)
            if not agent:
                raise ValidationError(f"Step '{step_name}' agent '{agent_id}' is not deployed")

            logger.info("Pipeline %s step %d/%d: agent=%s", pipeline_id, i + 1, len(steps), agent_id)
            ctx = _make_context(current_input)
            current_input = await agent.process(current_input, ctx)
            logger.info("Step %d complete: output_len=%d", i + 1, len(current_input))

        async with AsyncSessionLocal() as session:
            async with session.begin():
                run = await session.get(PipelineRun, pipeline_run.id)
                if run:
                    run.status = "completed"
                    run.output = json.dumps({"text": current_input})
                    run.completed_at = datetime.now(timezone.utc)

        pipeline_run.status = "completed"
        pipeline_run.output = json.dumps({"text": current_input})
        pipeline_run.completed_at = datetime.now(timezone.utc)

    except Exception as exc:
        logger.error("Pipeline %s failed at run %s: %s", pipeline_id, pipeline_run.id, exc)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                run = await session.get(PipelineRun, pipeline_run.id)
                if run:
                    run.status = "failed"
                    run.error = str(exc)
                    run.completed_at = datetime.now(timezone.utc)

        pipeline_run.status = "failed"
        pipeline_run.error = str(exc)
        pipeline_run.completed_at = datetime.now(timezone.utc)

    return pipeline_run
