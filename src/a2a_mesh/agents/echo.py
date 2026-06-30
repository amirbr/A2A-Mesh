"""Echo Agent — returns input text unchanged. Week 2 reference implementation."""

from a2a.server.agent_execution import RequestContext

from a2a_mesh.agents.base import AgentConfig, BaseAgent, SkillConfig

BASE_URL = "http://localhost:8000/a2a/echo"
RPC_URL = "/a2a/echo/"


class EchoAgent(BaseAgent):
    """Echoes the user's message back verbatim."""

    async def process(self, message: str, context: RequestContext) -> str:
        self._logger.info("Echo received: %r", message)
        return f"Echo: {message}" if message else "Echo: (empty)"


def build_echo_routes() -> tuple[list, list]:  # type: ignore[type-arg]
    """Return (agent_card_routes, jsonrpc_routes) for the echo agent."""
    config = AgentConfig(
        name="echo-agent",
        display_name="Echo Agent",
        description="Echoes back whatever you send — a2a-mesh reference agent",
        system_prompt="",
        skills=[
            SkillConfig(
                id="echo",
                name="Echo",
                description="Returns the input text unchanged",
                tags=["echo", "demo"],
                examples=["Hello!", "testing 1 2 3"],
            )
        ],
    )
    agent = EchoAgent(config)
    return agent.build_routes(base_url=BASE_URL, rpc_url=RPC_URL)
