"""GenericAgent — a configurable agent driven by system prompt + Claude."""

import logging
import shutil
import tempfile
from pathlib import Path

from a2a.server.agent_execution import RequestContext

from a2a_mesh.agents.base import BaseAgent
from a2a_mesh.agents.mcp_client import call_tool as mcp_call_tool
from a2a_mesh.agents.mcp_client import discover_tools as mcp_discover_tools
from a2a_mesh.agents.tools import BUILTIN_TOOL_SCHEMAS, Workspace, execute_builtin_tool
from a2a_mesh.db.models.agent import Agent
from a2a_mesh.db.session import AsyncSessionLocal
from a2a_mesh.llm import dispatch

logger = logging.getLogger(__name__)


class GenericAgent(BaseAgent):
    """Agent whose behaviour is defined entirely by its system_prompt config.

    Calls Claude with the configured system prompt and returns the response.
    Falls back to a stub if no API key is set (useful in tests).
    """

    def __init__(self, config, agent_db_id: str | None = None) -> None:  # type: ignore[override]
        super().__init__(config)
        self._agent_db_id = agent_db_id

    async def process(self, message: str, context: RequestContext) -> str:
        if not message:
            return "(no input)"

        try:
            if self.config.tools or self.config.mcp_servers:
                return await self._process_with_tools(message)
            return await dispatch.complete(
                provider=self.config.provider,
                system_prompt=self.config.system_prompt,
                user_message=message,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        except Exception as exc:
            logger.error(
                "LLM call failed for agent %s (provider=%s): %s",
                self.config.name,
                self.config.provider,
                exc,
            )
            raise

    async def _process_with_tools(self, message: str) -> str:
        """Run the tool-calling loop in a fresh, isolated workspace for this task.

        Combines built-in tools (`config.tools`) with tools discovered from each of the
        agent's `config.mcp_servers` through the same loop — the model sees one flat list
        of tools and doesn't know or care which are local vs. MCP-provided.
        """
        schemas = [BUILTIN_TOOL_SCHEMAS[name] for name in self.config.tools if name in BUILTIN_TOOL_SCHEMAS]

        mcp_tool_servers: dict[str, str] = {}
        for server_url in self.config.mcp_servers:
            for schema in await mcp_discover_tools(server_url):
                name = schema["function"]["name"]
                mcp_tool_servers[name] = server_url
                schemas.append(schema)

        workspace_dir = Path(tempfile.mkdtemp(prefix=f"{self.config.name}-"))
        workspace = Workspace(workspace_dir)
        try:

            async def tool_executor(name: str, args: dict) -> str:  # type: ignore[type-arg]
                if name in mcp_tool_servers:
                    return await mcp_call_tool(mcp_tool_servers[name], name, args)
                return await execute_builtin_tool(workspace, name, args)

            return await dispatch.run_with_tools(
                provider=self.config.provider,
                system_prompt=self.config.system_prompt,
                user_message=message,
                model=self.config.model,
                tools=schemas,
                tool_executor=tool_executor,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        finally:
            shutil.rmtree(workspace_dir, ignore_errors=True)

    async def on_error(self, exc: Exception, user_text: str) -> None:
        """Mark agent as error in DB and unregister from registry on crash."""
        await super().on_error(exc, user_text)
        if self._agent_db_id:
            try:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        db_agent = await session.get(Agent, self._agent_db_id)
                        if db_agent:
                            db_agent.status = "error"
            except Exception as db_exc:
                logger.error("Failed to mark agent %s as error: %s", self._agent_db_id, db_exc)

            from a2a_mesh.orchestrator import registry
            registry.unregister(self._agent_db_id)
