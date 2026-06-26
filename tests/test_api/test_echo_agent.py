"""Tests for the Echo Agent A2A endpoints."""

import pytest
from httpx import AsyncClient


SEND_MESSAGE_PAYLOAD = {
    "jsonrpc": "2.0",
    "id": "1",
    "method": "SendMessage",
    "params": {
        "message": {
            "messageId": "msg-test-001",
            "role": "ROLE_USER",
            "parts": [{"text": "hello a2a-mesh"}],
        }
    },
}

A2A_HEADERS = {"A2A-Version": "1.0", "Content-Type": "application/json"}


class TestAgentCard:
    async def test_agent_card_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/.well-known/agent-card.json")
        assert response.status_code == 200

    async def test_agent_card_has_required_fields(self, client: AsyncClient) -> None:
        response = await client.get("/.well-known/agent-card.json")
        body = response.json()
        assert body["name"] == "echo-agent"
        assert "skills" in body
        assert len(body["skills"]) > 0

    async def test_agent_card_content_type_is_json(self, client: AsyncClient) -> None:
        response = await client.get("/.well-known/agent-card.json")
        assert "application/json" in response.headers["content-type"]


class TestSendMessage:
    async def test_send_message_returns_200(self, client: AsyncClient) -> None:
        response = await client.post("/a2a/echo/", headers=A2A_HEADERS, json=SEND_MESSAGE_PAYLOAD)
        assert response.status_code == 200

    async def test_send_message_echoes_text(self, client: AsyncClient) -> None:
        response = await client.post("/a2a/echo/", headers=A2A_HEADERS, json=SEND_MESSAGE_PAYLOAD)
        body = response.json()
        assert "result" in body
        result = body["result"]
        # Response is a Message with parts
        message = result.get("message") or result
        parts = message.get("parts", [])
        assert any("Echo: hello a2a-mesh" in str(p) for p in parts)

    async def test_send_message_without_version_header_fails(self, client: AsyncClient) -> None:
        response = await client.post(
            "/a2a/echo/",
            headers={"Content-Type": "application/json"},
            json=SEND_MESSAGE_PAYLOAD,
        )
        body = response.json()
        # SDK rejects requests without A2A-Version header
        assert "error" in body

    async def test_send_message_missing_message_id_fails(self, client: AsyncClient) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "SendMessage",
            "params": {
                "message": {
                    "role": "ROLE_USER",
                    "parts": [{"text": "no message id"}],
                }
            },
        }
        response = await client.post("/a2a/echo/", headers=A2A_HEADERS, json=payload)
        body = response.json()
        assert "error" in body
        assert body["error"]["code"] == -32602  # validation error

    async def test_send_message_empty_text_echoes_empty(self, client: AsyncClient) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": "msg-empty-001",
                    "role": "ROLE_USER",
                    "parts": [{"text": ""}],
                }
            },
        }
        response = await client.post("/a2a/echo/", headers=A2A_HEADERS, json=payload)
        assert response.status_code == 200
        body = response.json()
        assert "result" in body
