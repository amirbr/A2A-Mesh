"""Echo Agent — returns input text unchanged. Week 2 reference implementation."""

import logging

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

from a2a_mesh.db.task_store import PostgresTaskStore

logger = logging.getLogger(__name__)

ECHO_AGENT_URL = "http://localhost:8000/a2a/echo"


class EchoAgentExecutor(AgentExecutor):
    """Echoes the user's message back verbatim."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle a SendMessage or SendStreamingMessage request."""
        user_text = get_message_text(context.message) or "(empty)"
        logger.info("Echo agent received: %r", user_text)
        reply = new_text_message(text=f"Echo: {user_text}")
        await event_queue.enqueue_event(reply)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel is a no-op for the echo agent."""
        pass


def _build_agent_card() -> AgentCard:
    return AgentCard(
        name="echo-agent",
        description="Echoes back whatever you send — a2a-mesh reference agent",
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(url=ECHO_AGENT_URL, protocol_binding="jsonrpc"),
        ],
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="echo",
                name="Echo",
                description="Returns the input text unchanged",
                tags=["echo", "demo"],
                examples=["Hello!", "testing 1 2 3"],
            )
        ],
    )


def build_echo_routes() -> tuple[list, list]:
    """Return (agent_card_routes, jsonrpc_routes) for the echo agent.

    Mount with:
        add_a2a_routes_to_fastapi(app, agent_card_routes=card, jsonrpc_routes=rpc)
    """
    agent_card = _build_agent_card()
    task_store = PostgresTaskStore(agent_id="echo")
    executor = EchoAgentExecutor()
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        agent_card=agent_card,
    )
    card_routes = create_agent_card_routes(agent_card)
    rpc_routes = create_jsonrpc_routes(handler, rpc_url="/a2a/echo/")
    return card_routes, rpc_routes
