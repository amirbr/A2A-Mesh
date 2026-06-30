"""Tests for /v1/auth/* endpoints."""

import pytest
from httpx import AsyncClient


REGISTER_BODY = {
    "company_name": "Test Corp",
    "namespace": "testcorp",
    "email": "admin@testcorp.com",
    "password": "strongpassword123",
}


class TestRegister:
    async def test_register_returns_201_and_token(self, client: AsyncClient) -> None:
        response = await client.post("/v1/auth/register", json=REGISTER_BODY)
        assert response.status_code == 201
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_register_duplicate_namespace_fails(self, client: AsyncClient) -> None:
        await client.post("/v1/auth/register", json=REGISTER_BODY)
        response = await client.post("/v1/auth/register", json=REGISTER_BODY)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"

    async def test_register_invalid_email_fails(self, client: AsyncClient) -> None:
        body = {**REGISTER_BODY, "email": "not-an-email", "namespace": "other"}
        response = await client.post("/v1/auth/register", json=body)
        assert response.status_code == 422


class TestLogin:
    async def test_login_returns_token(self, client: AsyncClient) -> None:
        await client.post("/v1/auth/register", json=REGISTER_BODY)
        response = await client.post(
            "/v1/auth/login",
            json={"email": REGISTER_BODY["email"], "password": REGISTER_BODY["password"]},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_login_wrong_password_fails(self, client: AsyncClient) -> None:
        await client.post("/v1/auth/register", json=REGISTER_BODY)
        response = await client.post(
            "/v1/auth/login",
            json={"email": REGISTER_BODY["email"], "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "auth_required"

    async def test_login_unknown_email_fails(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/auth/login",
            json={"email": "ghost@example.com", "password": "whatever"},
        )
        assert response.status_code == 401


class TestApiKeys:
    async def _get_token(self, client: AsyncClient) -> str:
        r = await client.post("/v1/auth/register", json={**REGISTER_BODY, "namespace": "apikeytest"})
        return r.json()["access_token"]

    async def test_create_api_key_returns_raw_key(self, client: AsyncClient) -> None:
        token = await self._get_token(client)
        response = await client.post(
            "/v1/auth/api-keys",
            json={"name": "ci-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        body = response.json()
        assert "key" in body
        assert len(body["key"]) > 8
        assert body["prefix"] == body["key"][:8]

    async def test_list_api_keys(self, client: AsyncClient) -> None:
        token = await self._get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/v1/auth/api-keys", json={"name": "key-1"}, headers=headers)
        await client.post("/v1/auth/api-keys", json={"name": "key-2"}, headers=headers)
        response = await client.get("/v1/auth/api-keys", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_revoke_api_key(self, client: AsyncClient) -> None:
        token = await self._get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        create_r = await client.post("/v1/auth/api-keys", json={"name": "temp"}, headers=headers)
        key_id = create_r.json()["id"]
        delete_r = await client.delete(f"/v1/auth/api-keys/{key_id}", headers=headers)
        assert delete_r.status_code == 204
        # should no longer appear in list
        list_r = await client.get("/v1/auth/api-keys", headers=headers)
        assert all(k["id"] != key_id for k in list_r.json())

    async def test_api_keys_require_auth(self, client: AsyncClient) -> None:
        response = await client.get("/v1/auth/api-keys")
        assert response.status_code == 401
