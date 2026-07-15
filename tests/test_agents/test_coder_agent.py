"""End-to-end test: Coder config + GenericAgent's tool loop against real tools.

The LLM call is scripted (mocked at the `litellm.acompletion` boundary, never the real API),
but the tool execution is real — real files get written to a real temp workspace and a real
`pytest` subprocess runs against them. This proves the Section A/B/C pieces actually work
together, not just that they're wired to mocks of each other.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from a2a_mesh.agents.coder import build_coder_config
from a2a_mesh.agents.generic import GenericAgent
from a2a_mesh.api.a2a.dispatch import _build_context, _parse_message

LOGIN_CODE = (
    '_USERS = {"alice": "hunter2"}\n\n'
    "def login(username, password):\n"
    "    return _USERS.get(username) == password\n"
)

LOGIN_TEST = (
    "from login import login\n\n"
    "def test_login_success():\n"
    '    assert login("alice", "hunter2") is True\n\n'
    "def test_login_failure():\n"
    '    assert login("alice", "wrong") is False\n'
)


def _make_context() -> object:
    return _build_context(
        _parse_message(
            {
                "message": {
                    "messageId": "msg-001",
                    "role": "ROLE_USER",
                    "parts": [{"text": "add a Flask login endpoint"}],
                }
            }
        )
    )


def _tool_call_response(call_id: str, name: str, arguments: dict) -> SimpleNamespace:  # type: ignore[type-arg]
    function = SimpleNamespace(name=name, arguments=json.dumps(arguments))
    tool_call = SimpleNamespace(id=call_id, function=function)
    message = SimpleNamespace(content=None, tool_calls=[tool_call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _final_response(content: str) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.mark.asyncio
async def test_coder_agent_writes_code_and_verifies_with_tests() -> None:
    """'add a Flask login endpoint' → real files written, real pytest run, tests pass."""
    agent = GenericAgent(build_coder_config())
    ctx = _make_context()

    script = [
        _tool_call_response("call_1", "file_write", {"path": "login.py", "content": LOGIN_CODE}),
        _tool_call_response("call_2", "file_write", {"path": "test_login.py", "content": LOGIN_TEST}),
        _tool_call_response("call_3", "run_tests", {}),
        _final_response("Done. Added login() and verified it with passing tests."),
    ]
    calls: list[dict] = []  # type: ignore[type-arg]

    async def fake_acompletion(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)  # type: ignore[arg-type]
        return script[len(calls) - 1]

    with patch("a2a_mesh.llm.dispatch.litellm.acompletion", side_effect=fake_acompletion):
        result = await agent.process("add a Flask login endpoint", ctx)

    assert "Done" in result

    # Confirm the tool result fed back to the model after run_tests shows a real, passing run.
    final_call_messages = calls[-1]["messages"]
    tool_messages = [m["content"] for m in final_call_messages if m.get("role") == "tool"]
    assert any("2 passed" in msg for msg in tool_messages)
