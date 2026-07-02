"""GenericAgent — a configurable agent driven by system prompt + LLM.

Week 4: stub response. Week 5: wires in Claude.
"""

import logging

from a2a.server.agent_execution import RequestContext

from a2a_mesh.agents.base import BaseAgent
from a2a_mesh.db.models.agent import Agent
from a2a_mesh.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


class GenericAgent(BaseAgent):
    """Agent whose behaviour is defined entirely by its system_prompt config.

    Currently returns a placeholder response. Week 5 replaces this with
    a real Claude API call using self.config.system_prompt.
    """

    def __init__(self, config, agent_db_id: str | None = None) -> None:  # type: ignore[override]
        super().__init__(config)
        self._agent_db_id = agent_db_id

    async def process(self, message: str, context: RequestContext) -> str:
        if not message:
            return "(no input)"
        # Week 5: return await llm.complete(self.config.system_prompt, message)
        return f"[{self.config.display_name}] received: {message}"

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
