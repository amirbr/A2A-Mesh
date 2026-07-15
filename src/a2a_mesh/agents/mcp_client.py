"""MCP client integration — resolves an agent's `mcp_servers` URLs into callable tools.

Uses the official `mcp` Python SDK (decision: official SDK over a hand-rolled JSON-RPC
client, 2026-07-15 — see PROGRESS.md) over the Streamable HTTP transport. Each MCP tool is
exposed through the same tool-calling loop as the built-ins in `agents/tools.py`: a schema
for the model, and an async call that resolves a `(name, args)` invocation to a string result.
"""

import logging
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult
from mcp.types import Tool as MCPTool

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0
DEPLOY_VALIDATION_TIMEOUT_SECONDS = 5.0


class McpServerError(Exception):
    """Raised when an MCP server is unreachable or its handshake/response is invalid."""


def _to_tool_schema(tool: MCPTool) -> dict[str, Any]:
    """Convert an MCP `Tool` definition to the LiteLLM function-calling schema shape."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }


def _extract_text(result: CallToolResult) -> str:
    """Flatten an MCP `CallToolResult`'s content blocks into a single string."""
    parts = [block.text for block in result.content if getattr(block, "type", None) == "text"]
    text = "\n".join(parts) if parts else "(empty tool result)"
    return f"Error: {text}" if result.isError else text


def _http_client(timeout: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(timeout), follow_redirects=True)


async def discover_tools(
    server_url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> list[dict[str, Any]]:
    """Connect to an MCP server and return its tools as LiteLLM function schemas.

    Raises:
        McpServerError: If the server is unreachable or the handshake fails.
    """
    try:
        async with (
            _http_client(timeout) as http_client,
            streamable_http_client(server_url, http_client=http_client) as (read_stream, write_stream, _),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            result = await session.list_tools()
            return [_to_tool_schema(t) for t in result.tools]
    except Exception as exc:
        raise McpServerError(f"could not reach MCP server '{server_url}': {exc}") from exc


async def call_tool(
    server_url: str, name: str, args: dict[str, Any], timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> str:
    """Call a tool on an MCP server and return its result as text.

    Never raises for a failed tool call — a connection/handshake failure comes back as an
    `"Error: ..."` string so the model can see it, same as `execute_builtin_tool`.
    """
    try:
        async with (
            _http_client(timeout) as http_client,
            streamable_http_client(server_url, http_client=http_client) as (read_stream, write_stream, _),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            result = await session.call_tool(name, args)
            return _extract_text(result)
    except Exception as exc:
        logger.warning("MCP call to '%s' on '%s' failed: %s", name, server_url, exc)
        return f"Error: MCP call to '{name}' on '{server_url}' failed: {exc}"
