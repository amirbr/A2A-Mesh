"""Tests for the LLM dispatch module — plain completion and the tool-calling loop."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from a2a_mesh.llm import dispatch


@pytest.fixture(autouse=True)
def mock_llm() -> None:
    """Override conftest's global dispatch.complete mock — this file tests the real thing."""
    yield


def _response(content: str | None, tool_calls: list[SimpleNamespace] | None = None) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _tool_call(call_id: str, name: str, arguments: dict[str, object]) -> SimpleNamespace:
    function = SimpleNamespace(name=name, arguments=json.dumps(arguments))
    return SimpleNamespace(id=call_id, function=function)


@pytest.mark.asyncio
async def test_complete_no_tools_unaffected() -> None:
    """complete() sends no `tools` kwarg and returns text as before — no regression."""
    with patch(
        "a2a_mesh.llm.dispatch.litellm.acompletion", new_callable=AsyncMock
    ) as mock_acompletion:
        mock_acompletion.return_value = _response("hello back")
        result = await dispatch.complete(
            provider="anthropic",
            system_prompt="be nice",
            user_message="hi",
            model="claude-opus-4-8",
        )

    assert result == "hello back"
    call_kwargs = mock_acompletion.call_args.kwargs
    assert "tools" not in call_kwargs
    assert call_kwargs["messages"] == [
        {"role": "system", "content": "be nice"},
        {"role": "user", "content": "hi"},
    ]


@pytest.mark.asyncio
async def test_run_with_tools_no_tool_calls_returns_immediately() -> None:
    """If the model never calls a tool, the loop returns on the first response."""
    with patch(
        "a2a_mesh.llm.dispatch.litellm.acompletion", new_callable=AsyncMock
    ) as mock_acompletion:
        mock_acompletion.return_value = _response("no tools needed")
        tool_executor = AsyncMock()
        result = await dispatch.run_with_tools(
            provider="anthropic",
            system_prompt="",
            user_message="hi",
            model="claude-opus-4-8",
            tools=[],
            tool_executor=tool_executor,
        )

    assert result == "no tools needed"
    tool_executor.assert_not_called()


@pytest.mark.asyncio
async def test_run_with_tools_round_trips_tool_call() -> None:
    """A tool call is executed and its result is fed back to produce a final answer."""
    tool_call = _tool_call("call_1", "file_read", {"path": "foo.py"})
    responses = [
        _response(None, tool_calls=[tool_call]),
        _response("the file says hello"),
    ]

    async def fake_acompletion(**kwargs: object) -> SimpleNamespace:
        return responses.pop(0)

    tool_executor = AsyncMock(return_value="file contents: hello")

    with patch("a2a_mesh.llm.dispatch.litellm.acompletion", side_effect=fake_acompletion):
        result = await dispatch.run_with_tools(
            provider="anthropic",
            system_prompt="you can read files",
            user_message="what's in foo.py?",
            model="claude-opus-4-8",
            tools=[{"type": "function", "function": {"name": "file_read", "parameters": {}}}],
            tool_executor=tool_executor,
        )

    assert result == "the file says hello"
    tool_executor.assert_called_once_with("file_read", {"path": "foo.py"})


@pytest.mark.asyncio
async def test_run_with_tools_raises_after_max_iterations() -> None:
    """A model that never stops calling tools trips the iteration cap."""
    tool_call = _tool_call("call_1", "loop_tool", {})

    with patch(
        "a2a_mesh.llm.dispatch.litellm.acompletion", new_callable=AsyncMock
    ) as mock_acompletion:
        mock_acompletion.return_value = _response(None, tool_calls=[tool_call])
        tool_executor = AsyncMock(return_value="ok")
        with pytest.raises(RuntimeError, match="max_iterations"):
            await dispatch.run_with_tools(
                provider="anthropic",
                system_prompt="",
                user_message="loop forever",
                model="claude-opus-4-8",
                tools=[{"type": "function", "function": {"name": "loop_tool", "parameters": {}}}],
                tool_executor=tool_executor,
                max_iterations=2,
            )
