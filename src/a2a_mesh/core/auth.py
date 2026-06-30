"""Password hashing, JWT creation/verification, and API key generation."""

import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from a2a_mesh.config import settings
from a2a_mesh.core.errors import AuthError

_ph = PasswordHasher()


# ── Passwords ────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password with argon2."""
    return _ph.hash(password)


def verify_password(plaintext: str, hashed: str) -> bool:
    """Return True if plaintext matches the stored hash."""
    try:
        return _ph.verify(hashed, plaintext)
    except VerifyMismatchError:
        return False


# ── JWT ──────────────────────────────────────────────────────────────────────

def create_token(user_id: str, company_id: str, role: str) -> str:
    """Issue a signed JWT for the given user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "company_id": company_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=settings.jwt_expiry_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:  # type: ignore[type-arg]
    """Decode and verify a JWT. Raises AuthError on failure."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AuthError(f"Invalid token: {exc}") from exc


# ── API Keys ─────────────────────────────────────────────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        (raw_key, key_hash, prefix) — store hash, show prefix in UI, return raw once.
    """
    raw = secrets.token_urlsafe(32)
    key_hash = _ph.hash(raw)
    prefix = raw[:8]
    return raw, key_hash, prefix


def verify_api_key(raw: str, key_hash: str) -> bool:
    """Return True if the raw API key matches the stored hash."""
    try:
        return _ph.verify(key_hash, raw)
    except VerifyMismatchError:
        return False
