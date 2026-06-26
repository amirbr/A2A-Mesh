"""
Minimal Echo Agent using the a2a-sdk — Week 1 sample.

Demonstrates the SDK's AgentExecutor interface and FastAPI integration.
Run with:
    uv run python scripts/run_echo_sample.py
Then in another terminal:
    curl -s -X POST http://localhost:9000/ \
      -H "Content-Type: application/json" \
      -H "x-a2a-version: 1.0" \
      -d '{"jsonrpc":"2.0","id":"1","method":"message/send",
           "params":{"message":{"role":"ROLE_USER",
                                "parts":[{"text":{"text":"hello"}}]}}}'
"""

import asyncio
import logging

import uvicorn
from a2a.helpers.proto_helpers import get_message_text, new_text_artifact
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue_v2 import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types.a2a_pb2 import (
    AgentCard,
    AgentCapabilities,
    AgentInterface,
    AgentSkill,
    TASK_STATE_COMPLETED,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:9000"


class EchoAgentExecutor(AgentExecutor):
    """Echoes the user's text back as a completed artifact."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        from a2a.helpers.proto_helpers import new_text_message
        user_text = get_message_text(context.message) or "(empty)"
        logger.info("Echo received: %r", user_text)
        reply = new_text_message(text=f"Echo: {user_text}")  # role defaults to ROLE_AGENT
        await event_queue.enqueue_event(reply)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def build_app() -> FastAPI:
    agent_card = AgentCard(
        name="echo-agent",
        description="Echoes back whatever you send",
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(url=BASE_URL, protocol_binding="jsonrpc"),
        ],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="echo",
                name="Echo",
                description="Returns the input unchanged",
                tags=["echo", "demo"],
                examples=["Hello!", "testing 1 2 3"],
            )
        ],
    )

    task_store = InMemoryTaskStore()
    executor = EchoAgentExecutor()
    handler = DefaultRequestHandler(agent_executor=executor, task_store=task_store, agent_card=agent_card)

    app = FastAPI(title="Echo Agent (A2A Sample)", version="1.0.0")
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url="/"),
    )
    return app


if __name__ == "__main__":
    app = build_app()
    logger.info("Echo Agent starting on %s", BASE_URL)
    logger.info("Agent Card: %s/.well-known/agent.json", BASE_URL)
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
