"""Token creation and the hashing used for OTP codes and refresh tokens.

Access tokens are short-lived signed JWTs (stateless). Refresh tokens are opaque random
strings stored hashed, so they can be revoked and rotated (see `api.services.auth`).
"""

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from api.core.config import Settings

ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - a claim value, not a secret


class InvalidTokenError(Exception):
    """The token is malformed, expired, or not of the expected type."""


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    role: str


def _secret(settings: Settings) -> str:
    return settings.jwt_secret.get_secret_value()


def create_access_token(settings: Settings, *, user_id: uuid.UUID, role: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "typ": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_token_ttl_s)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, _secret(settings), algorithm=settings.jwt_algorithm)


def decode_access_token(settings: Settings, token: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            _secret(settings),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "typ"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("unexpected token type")
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except ValueError as exc:
        raise InvalidTokenError("subject is not a user id") from exc
    role = payload.get("role")
    if not isinstance(role, str):
        raise InvalidTokenError("missing role")
    return AccessTokenClaims(user_id=user_id, role=role)


def generate_refresh_token() -> str:
    """A 256-bit opaque token. Only its hash is stored."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_otp_code(length: int) -> str:
    """A numeric code with a uniform distribution (no modulo bias)."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def hash_otp_code(settings: Settings, *, phone: str, code: str) -> str:
    """Keyed hash, so a leaked database alone does not allow brute-forcing short codes."""
    return hmac.new(
        _secret(settings).encode(), f"{phone}:{code}".encode(), hashlib.sha256
    ).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
