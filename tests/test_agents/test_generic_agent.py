"""Tests for GenericAgent with mocked LLM dispatch."""

from unittest.mock import AsyncMock, patch

import pytest

from a2a_mesh.agents.base import AgentConfig
from a2a_mesh.agents.generic import GenericAgent
from a2a_mesh.api.a2a.dispatch import _build_context, _parse_message


def _make_agent(
    system_prompt: str = "You are a helpful assistant.",
    provider: str = "anthropic",
    tools: list[str] | None = None,
    mcp_servers: list[str] | None = None,
) -> GenericAgent:
    config = AgentConfig(
        name="test-agent",
        display_name="Test Agent",
        description="A test agent",
        provider=provider,
        system_prompt=system_prompt,
        model="claude-opus-4-8",
        temperature=0.2,
        max_tokens=100,
        tools=tools or [],
        mcp_servers=mcp_servers or [],
    )
    return GenericAgent(config)


def _make_context() -> object:
    return _build_context(_parse_message({"message": {
        "messageId": "msg-001",
        "role": "ROLE_USER",
        "parts": [{"text": "hello"}],
    }}))


@pytest.mark.asyncio
async def test_process_calls_dispatch_and_returns_text() -> None:
    agent = _make_agent("You are a pirate.")
    ctx = _make_context()

    with patch("a2a_mesh.llm.dispatch.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = "Arrr, ahoy there!"
        result = await agent.process("hello", ctx)

    assert result == "Arrr, ahoy there!"
    mock_complete.assert_called_once_with(
        provider="anthropic",
        system_prompt="You are a pirate.",
        user_message="hello",
        model="claude-opus-4-8",
        temperature=0.2,
        max_tokens=100,
    )


@pytest.mark.asyncio
async def test_process_empty_message_returns_no_input() -> None:
    agent = _make_agent()
    ctx = _make_context()
    result = await agent.process("", ctx)
    assert result == "(no input)"


@pytest.mark.asyncio
async def test_process_propagates_llm_error() -> None:
    agent = _make_agent()
    ctx = _make_context()

    with patch("a2a_mesh.llm.dispatch.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = RuntimeError("API error")
        with pytest.raises(RuntimeError, match="API error"):
            await agent.process("hello", ctx)


@pytest.mark.asyncio
async def test_process_uses_system_prompt_from_config() -> None:
    agent = _make_agent("You are a reviewer. Be critical.")
    ctx = _make_context()

    with patch("a2a_mesh.llm.dispatch.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = "This code has issues."
        await agent.process("review this code", ctx)

    call_kwargs = mock_complete.call_args.kwargs
    assert call_kwargs["system_prompt"] == "You are a reviewer. Be critical."
    assert call_kwargs["user_message"] == "review this code"


@pytest.mark.asyncio
async def test_process_uses_ollama_provider() -> None:
    agent = _make_agent("You are a coder.", provider="ollama")
    ctx = _make_context()

    with patch("a2a_mesh.llm.dispatch.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = "def hello(): pass"
        result = await agent.process("write hello", ctx)

    assert result == "def hello(): pass"
    assert mock_complete.call_args.kwargs["provider"] == "ollama"


@pytest.mark.asyncio
async def test_process_without_tools_never_touches_tool_loop() -> None:
    """No-tools agent behaves exactly as before — no regression from Section A/B."""
    agent = _make_agent()
    ctx = _make_context()

    with (
        patch("a2a_mesh.llm.dispatch.complete", new_callable=AsyncMock) as mock_complete,
        patch("a2a_mesh.agents.generic.dispatch.run_with_tools", new_callable=AsyncMock) as mock_run,
    ):
        mock_complete.return_value = "hi"
        result = await agent.process("hello", ctx)

    assert result == "hi"
    mock_run.assert_not_called()


@pytest.mark.asyncio
async def test_process_with_tools_uses_tool_loop_and_cleans_up_workspace() -> None:
    agent = _make_agent(tools=["file_read", "file_write"])
    ctx = _make_context()

    with (
        patch("a2a_mesh.agents.generic.dispatch.run_with_tools", new_callable=AsyncMock) as mock_run,
        patch("a2a_mesh.agents.generic.shutil.rmtree") as mock_rmtree,
    ):
        mock_run.return_value = "done"
        result = await agent.process("write a file", ctx)

    assert result == "done"
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["provider"] == "anthropic"
    assert len(call_kwargs["tools"]) == 2
    assert callable(call_kwargs["tool_executor"])
    mock_rmtree.assert_called_once()


@pytest.mark.asyncio
async def test_process_calls_real_mcp_tool_and_uses_result(mock_mcp_server: str) -> None:
    """End-to-end: an agent with no built-in tools, only an mcp_servers entry, calls a real
    tool on a real local MCP server and the result reaches the model's final answer."""
    import json
    from types import SimpleNamespace

    agent = _make_agent(mcp_servers=[mock_mcp_server])
    ctx = _make_context()

    def _tool_call(call_id: str, name: str, arguments: dict) -> SimpleNamespace:  # type: ignore[type-arg]
        function = SimpleNamespace(name=name, arguments=json.dumps(arguments))
        message = SimpleNamespace(content=None, tool_calls=[SimpleNamespace(id=call_id, function=function)])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    def _final(content: str) -> SimpleNamespace:
        message = SimpleNamespace(content=content, tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    script = [
        _tool_call("call_1", "get_weather", {"city": "Boston"}),
        _final("It's sunny in Boston."),
    ]
    calls: list[dict] = []  # type: ignore[type-arg]

    async def fake_acompletion(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)  # type: ignore[arg-type]
        return script[len(calls) - 1]

    with patch("a2a_mesh.llm.dispatch.litellm.acompletion", side_effect=fake_acompletion):
        result = await agent.process("what's the weather in Boston?", ctx)

    assert result == "It's sunny in Boston."
    final_messages = calls[-1]["messages"]
    tool_messages = [m["content"] for m in final_messages if m.get("role") == "tool"]
    assert tool_messages == ["sunny in Boston"]

    # The model must have seen the MCP tool alongside any built-ins (none configured here).
    first_call_tools = calls[0]["tools"]
    assert any(t["function"]["name"] == "get_weather" for t in first_call_tools)
