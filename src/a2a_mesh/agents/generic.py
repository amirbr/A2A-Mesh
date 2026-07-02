"""GenericAgent — a configurable agent driven by system prompt + LLM.

Week 4: echoes back (stub). Week 5: wires in Claude.
"""

from a2a.server.agent_execution import RequestContext

from a2a_mesh.agents.base import BaseAgent


class GenericAgent(BaseAgent):
    """Agent whose behaviour is defined entirely by its system_prompt config.

    Currently returns a placeholder response. Week 5 replaces this with
    a real Claude API call using self.config.system_prompt.
    """

    async def process(self, message: str, context: RequestContext) -> str:
        if not message:
            return "(no input)"
        # Week 5: return await llm.complete(self.config.system_prompt, message)
        return f"[{self.config.display_name}] received: {message}"
