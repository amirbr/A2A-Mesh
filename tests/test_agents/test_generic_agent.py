"""Tests for GenericAgent with mocked LLM dispatch."""

from unittest.mock import AsyncMock, patch

import pytest

from a2a_mesh.agents.base import AgentConfig
from a2a_mesh.agents.generic import GenericAgent
from a2a_mesh.api.a2a.dispatch import _build_context, _parse_message


def _make_agent(
    system_prompt: str = "You are a helpful assistant.",
    provider: str = "anthropic",
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
