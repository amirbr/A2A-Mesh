"""Dynamic A2A dispatch — routes /a2a/{agent_id}/ calls to the registry."""

import logging

from a2a.helpers.proto_helpers import get_message_text, new_text_message
from a2a.server.agent_execution import RequestContext
from a2a.server.agent_execution.context import ServerCallContext
from a2a.types.a2a_pb2 import Message, SendMessageRequest
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from google.protobuf import json_format

from a2a_mesh.core.errors import NotFoundError
from a2a_mesh.orchestrator import registry

logger = logging.getLogger(__name__)
router = APIRouter(tags=["a2a-dispatch"])


def _build_context(message: Message) -> RequestContext:
    """Build a minimal RequestContext for in-process dispatch."""
    request = SendMessageRequest(message=message)
    return RequestContext(
        call_context=ServerCallContext(),
        request=request,
    )


def _parse_message(params: dict) -> Message:  # type: ignore[type-arg]
    msg = Message()
    json_format.ParseDict(params.get("message", {}), msg)
    return msg


@router.post("/a2a/{agent_id}/")
async def dispatch(agent_id: str, request: Request) -> JSONResponse:
    """Dispatch a JSON-RPC SendMessage call to the registered agent."""
    body = await request.json()
    rpc_id = body.get("id", "1")

    agent = registry.get(agent_id)
    if not agent:
        return JSONResponse(
            status_code=404,
            content={
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32001, "message": f"Agent '{agent_id}' is not deployed"},
            },
        )

    method = body.get("method")
    if method != "SendMessage":
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32601, "message": f"Method '{method}' not supported"},
            }
        )

    try:
        message = _parse_message(body.get("params", {}))
    except Exception as exc:
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32602, "message": f"Invalid params: {exc}"},
            }
        )

    try:
        ctx = _build_context(message)
        user_text = get_message_text(message) or ""
        response_text = await agent.process(user_text, ctx)
    except Exception as exc:
        logger.exception("Agent %s raised during dispatch", agent_id)
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32000, "message": f"Agent error: {exc}"},
            }
        )

    reply = new_text_message(text=response_text)
    reply_dict = json_format.MessageToDict(reply, preserving_proto_field_name=True)
    return JSONResponse(content={"jsonrpc": "2.0", "id": rpc_id, "result": {"message": reply_dict}})


@router.get("/a2a/{agent_id}/.well-known/agent-card.json")
async def agent_card(agent_id: str) -> JSONResponse:
    """Return the AgentCard for a deployed agent."""
    agent = registry.get(agent_id)
    if not agent:
        raise NotFoundError("Agent")

    base_url = f"http://localhost:8000/a2a/{agent_id}/"
    card = agent.build_agent_card(base_url)
    card_dict = json_format.MessageToDict(card, preserving_proto_field_name=True)
    return JSONResponse(content=card_dict)
