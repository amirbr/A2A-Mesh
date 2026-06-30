"""Auth routes: register, login, API key management."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from a2a_mesh.core.auth import (
    create_token,
    decode_token,
    generate_api_key,
    hash_password,
    verify_password,
)
from a2a_mesh.core.errors import AuthError, ConflictError, ForbiddenError, NotFoundError
from a2a_mesh.core.ids import api_key_id, company_id, user_id
from a2a_mesh.db.models.api_key import ApiKey
from a2a_mesh.db.models.company import Company
from a2a_mesh.db.models.user import User
from a2a_mesh.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/auth", tags=["auth"])
_bearer = HTTPBearer()


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    company_name: str
    namespace: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CreateApiKeyRequest(BaseModel):
    name: str
    expires_at: str | None = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    created_at: str


class CreateApiKeyResponse(ApiKeyResponse):
    key: str  # raw key — shown once only


# ── Auth dependency ───────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict:  # type: ignore[type-arg]
    """FastAPI dependency — decode JWT and return claims."""
    return decode_token(credentials.credentials)


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest) -> TokenResponse:
    """Create a new company and its first admin user."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            existing = await session.execute(
                select(Company).where(Company.namespace == body.namespace)
            )
            if existing.scalar_one_or_none():
                raise ConflictError(f"Namespace '{body.namespace}' already taken")

            co = Company(
                id=company_id(),
                name=body.company_name,
                namespace=body.namespace,
                plan="free",
            )
            session.add(co)

            u = User(
                id=user_id(),
                company_id=co.id,
                email=body.email,
                password_hash=hash_password(body.password),
                role="admin",
            )
            session.add(u)

    logger.info("Registered company %s user %s", co.id, u.id)
    token = create_token(user_id=u.id, company_id=co.id, role=u.role)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """Authenticate and return a JWT."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise AuthError("Invalid email or password")

    token = create_token(user_id=user.id, company_id=user.company_id, role=user.role)
    return TokenResponse(access_token=token)


@router.post("/api-keys", response_model=CreateApiKeyResponse, status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    claims: Annotated[dict, Depends(get_current_user)],  # type: ignore[type-arg]
) -> CreateApiKeyResponse:
    """Generate a new API key for the current company."""
    raw, key_hash, prefix = generate_api_key()
    key_id = api_key_id()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            key = ApiKey(
                id=key_id,
                company_id=claims["company_id"],
                key_hash=key_hash,
                prefix=prefix,
                name=body.name,
            )
            session.add(key)
            await session.flush()
            created_at = key.created_at.isoformat()

    return CreateApiKeyResponse(
        id=key_id,
        name=body.name,
        prefix=prefix,
        key=raw,
        created_at=created_at,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    claims: Annotated[dict, Depends(get_current_user)],  # type: ignore[type-arg]
) -> list[ApiKeyResponse]:
    """List active API keys for the current company."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.company_id == claims["company_id"],
                ApiKey.revoked.is_(False),
            )
        )
        keys = result.scalars().all()

    return [
        ApiKeyResponse(id=k.id, name=k.name, prefix=k.prefix, created_at=k.created_at.isoformat())
        for k in keys
    ]


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    claims: Annotated[dict, Depends(get_current_user)],  # type: ignore[type-arg]
) -> None:
    """Revoke an API key."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            key = await session.get(ApiKey, key_id)
            if not key:
                raise NotFoundError("API key")
            if key.company_id != claims["company_id"]:
                raise ForbiddenError()
            key.revoked = True
