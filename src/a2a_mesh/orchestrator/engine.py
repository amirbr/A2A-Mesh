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


def _loop_condition_met(output_text: str, loop_until: dict[str, Any]) -> tuple[bool, str]:
    """Check a step's `loop_until` condition against its JSON output.

    Args:
        output_text: The step's raw text output — expected to be a JSON object (e.g. the
            Reviewer's `{"approved": bool, "feedback": str}`).
        loop_until: `{"field": <key>, "equals": <value>}` from the step config.

    Returns:
        (condition_met, feedback) — feedback is the output's `"feedback"` key if present,
        else the raw output text, used to build the retry message when not met.

    Raises:
        ValidationError: output_text isn't a JSON object, so the condition can't be evaluated.
    """
    field = loop_until.get("field", "")
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"loop_until step output is not valid JSON (field='{field}'): {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ValidationError(
            f"loop_until step output must be a JSON object, got {type(parsed).__name__}"
        )
    feedback = str(parsed.get("feedback", output_text))
    return parsed.get(field) == loop_until.get("equals"), feedback


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
    loop_attempts: dict[int, int] = {}
    try:
        i = 0
        while i < len(steps):
            step = steps[i]
            agent_id = step.get("agent_id", "")
            step_name = step.get("name", agent_id)
            agent = registry.get(agent_id)
            if not agent:
                raise ValidationError(f"Step '{step_name}' agent '{agent_id}' is not deployed")

            logger.info("Pipeline %s step %d/%d: agent=%s", pipeline_id, i + 1, len(steps), agent_id)
            ctx = _make_context(current_input)
            current_input = await agent.process(current_input, ctx)
            logger.info("Step %d complete: output_len=%d", i + 1, len(current_input))

            loop_until = step.get("loop_until")
            if loop_until:
                if i == 0:
                    raise ValidationError(
                        f"Step '{step_name}' has loop_until but is the first step — nothing to loop back to"
                    )
                max_iterations = step.get("max_iterations") or 3
                attempt = loop_attempts.get(i, 0) + 1
                loop_attempts[i] = attempt
                condition_met, feedback = _loop_condition_met(current_input, loop_until)
                if not condition_met:
                    if attempt >= max_iterations:
                        raise ValidationError(
                            f"Step '{step_name}' did not satisfy loop_until after {max_iterations} attempts"
                        )
                    logger.info(
                        "Step %d loop_until not met (attempt %d/%d) — looping back to step %d",
                        i + 1, attempt, max_iterations, i,
                    )
                    current_input = (
                        f"{input_text}\n\nA previous attempt was reviewed and rejected. "
                        f"Reviewer feedback: {feedback}\n\n"
                        "Revise your implementation to address this feedback."
                    )
                    i -= 1
                    continue

            i += 1

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
