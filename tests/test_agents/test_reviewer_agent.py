"""Tests for the Reviewer agent config and its structured JSON output.

Uses the autouse `mock_llm` fixture (patches `dispatch.complete` directly) rather than
patching `litellm.acompletion`, since the Reviewer has no tools configured and goes through
`GenericAgent.process()`'s plain `complete()` path, not the tool-calling loop.
"""

import json

import pytest

from a2a_mesh.agents.generic import GenericAgent
from a2a_mesh.agents.reviewer import build_reviewer_config
from a2a_mesh.api.a2a.dispatch import _build_context, _parse_message

CODE_UNDER_REVIEW = (
    "Task: add a login() function.\n\n"
    "login.py:\n"
    '_USERS = {"alice": "hunter2"}\n\n'
    "def login(username, password):\n"
    "    return _USERS.get(username) == password\n"
)


def _make_context(text: str) -> object:
    return _build_context(
        _parse_message(
            {
                "message": {
                    "messageId": "msg-001",
                    "role": "ROLE_USER",
                    "parts": [{"text": text}],
                }
            }
        )
    )


@pytest.mark.asyncio
async def test_reviewer_approves_correct_code(mock_llm) -> None:  # type: ignore[no-untyped-def]
    mock_llm.return_value = '{"approved": true, "feedback": "Looks correct."}'
    agent = GenericAgent(build_reviewer_config())
    ctx = _make_context(CODE_UNDER_REVIEW)

    result = await agent.process(CODE_UNDER_REVIEW, ctx)

    parsed = json.loads(result)
    assert parsed["approved"] is True
    assert isinstance(parsed["feedback"], str)


@pytest.mark.asyncio
async def test_reviewer_rejects_with_feedback(mock_llm) -> None:  # type: ignore[no-untyped-def]
    mock_llm.return_value = '{"approved": false, "feedback": "login() does not hash passwords."}'
    agent = GenericAgent(build_reviewer_config())
    ctx = _make_context(CODE_UNDER_REVIEW)

    result = await agent.process(CODE_UNDER_REVIEW, ctx)

    parsed = json.loads(result)
    assert parsed["approved"] is False
    assert "hash" in parsed["feedback"]


@pytest.mark.asyncio
async def test_reviewer_has_no_tools_configured() -> None:
    """Reviewer only reads text handed to it by the pipeline — no filesystem access."""
    config = build_reviewer_config()
    assert config.tools == []
    assert config.mcp_servers == []
