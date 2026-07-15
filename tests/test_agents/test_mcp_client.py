"""Tests for the MCP client against a real local MCP server (see conftest.mock_mcp_server)."""

import pytest

from a2a_mesh.agents.mcp_client import McpServerError, call_tool, discover_tools


@pytest.mark.asyncio
async def test_discover_tools_returns_schema_for_server_tool(mock_mcp_server: str) -> None:
    schemas = await discover_tools(mock_mcp_server)

    names = [s["function"]["name"] for s in schemas]
    assert "get_weather" in names

    weather_schema = next(s for s in schemas if s["function"]["name"] == "get_weather")
    assert weather_schema["type"] == "function"
    assert "city" in weather_schema["function"]["parameters"]["properties"]


@pytest.mark.asyncio
async def test_call_tool_returns_real_result(mock_mcp_server: str) -> None:
    result = await call_tool(mock_mcp_server, "get_weather", {"city": "Boston"})
    assert result == "sunny in Boston"


@pytest.mark.asyncio
async def test_call_tool_unknown_tool_returns_error_string(mock_mcp_server: str) -> None:
    result = await call_tool(mock_mcp_server, "not_a_real_tool", {})
    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_discover_tools_unreachable_server_raises() -> None:
    with pytest.raises(McpServerError, match="could not reach"):
        await discover_tools("http://127.0.0.1:1/mcp", timeout=2.0)
