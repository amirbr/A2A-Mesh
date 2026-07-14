"""BaseAgent — abstract base class for all A2A-Mesh agents."""

import logging
from abc import ABC, abstractmethod

from a2a.helpers.proto_helpers import get_message_text, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue_v2 import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.types.a2a_pb2 import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from pydantic import BaseModel

from a2a_mesh.db.task_store import PostgresTaskStore

logger = logging.getLogger(__name__)


class SkillConfig(BaseModel):
    """Config for a single agent skill exposed in the AgentCard."""

    id: str
    name: str
    description: str
    tags: list[str] = []
    examples: list[str] = []


class AgentConfig(BaseModel):
    """Runtime configuration for an agent instance."""

    name: str
    display_name: str
    description: str
    version: str = "1.0.0"
    provider: str = "anthropic"
    model: str = "claude-opus-4-8"
    temperature: float = 0.2
    max_tokens: int = 4096
    system_prompt: str = ""
    skills: list[SkillConfig] = []
    streaming: bool = False
    tools: list[str] = []
    mcp_servers: list[str] = []


class BaseAgent(AgentExecutor, ABC):
    """Abstract base class for all A2A-Mesh agents.

    Subclasses implement `process()`. Everything else — AgentCard generation,
    route building, error handling, lifecycle hooks — is handled here.

    Lifecycle hooks (override as needed):
        on_start()  — called when the agent is first loaded
        on_stop()   — called on shutdown
        on_error()  — called when process() raises
    """

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self._logger = logging.getLogger(f"agent.{config.name}")

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    async def on_start(self) -> None:
        """Called once when the agent starts. Override to warm up resources."""

    async def on_stop(self) -> None:
        """Called on shutdown. Override to clean up resources."""

    async def on_error(self, exc: Exception, user_text: str) -> None:
        """Called when process() raises. Override for custom error handling."""
        self._logger.error("Agent error processing %r: %s", user_text[:100], exc)

    # ── Core interface ────────────────────────────────────────────────────────

    @abstractmethod
    async def process(self, message: str, context: RequestContext) -> str:
        """Process a user message and return the agent's text response.

        Args:
            message: The user's text input.
            context: Full A2A request context (includes task_id, context_id, etc.).

        Returns:
            The agent's text response.
        """

    # ── SDK AgentExecutor implementation ──────────────────────────────────────

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle a SendMessage or SendStreamingMessage call."""
        user_text = get_message_text(context.message) or ""
        self._logger.info("Received message (len=%d)", len(user_text))
        try:
            response_text = await self.process(user_text, context)
            await event_queue.enqueue_event(new_text_message(text=response_text))
        except Exception as exc:
            await self.on_error(exc, user_text)
            raise

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel is a no-op by default."""

    # ── A2A route helpers ─────────────────────────────────────────────────────

    def build_agent_card(self, base_url: str) -> AgentCard:
        """Build the AgentCard proto from this agent's config."""
        return AgentCard(
            name=self.config.name,
            description=self.config.description,
            version=self.config.version,
            supported_interfaces=[
                AgentInterface(url=base_url, protocol_binding="jsonrpc"),
            ],
            capabilities=AgentCapabilities(streaming=self.config.streaming),
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
            skills=[
                AgentSkill(
                    id=s.id,
                    name=s.name,
                    description=s.description,
                    tags=s.tags,
                    examples=s.examples,
                )
                for s in self.config.skills
            ],
        )

    def build_routes(self, base_url: str, rpc_url: str) -> tuple[list, list]:  # type: ignore[type-arg]
        """Return (agent_card_routes, jsonrpc_routes) ready for FastAPI.

        Args:
            base_url: Public URL of this agent (e.g. "http://localhost:8000/a2a/echo").
            rpc_url:  FastAPI path for the JSON-RPC endpoint (e.g. "/a2a/echo/").
        """
        agent_card = self.build_agent_card(base_url)
        task_store = PostgresTaskStore(agent_id=self.config.name)
        handler = DefaultRequestHandler(
            agent_executor=self,
            task_store=task_store,
            agent_card=agent_card,
        )
        return (
            create_agent_card_routes(agent_card),
            create_jsonrpc_routes(handler, rpc_url=rpc_url),
        )
