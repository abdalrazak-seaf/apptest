"""Shared FastAPI dependencies: database session, Redis, settings, and authentication."""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import Settings, get_settings
from api.core.db import get_session
from api.core.errors import forbidden, unauthorized
from api.core.redis import get_redis
from api.core.security import InvalidTokenError, decode_access_token
from api.integrations.sms import SmsProvider, get_sms_provider
from api.models.enums import UserRole
from api.models.user import User

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RedisDep = Annotated[Redis, Depends(get_redis)]
SmsDep = Annotated[SmsProvider, Depends(get_sms_provider)]

# auto_error=False so that a missing header produces our own error code, not FastAPI's.
_bearer = HTTPBearer(auto_error=False, description="Access token from /auth/verify")
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


async def get_current_user(
    credentials: BearerDep, session: SessionDep, settings: SettingsDep
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        claims = decode_access_token(settings, credentials.credentials)
    except InvalidTokenError as exc:
        raise unauthorized("access_token_invalid") from exc

    user = await session.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise unauthorized("access_token_invalid")
    return user


async def get_optional_user(
    credentials: BearerDep, session: SessionDep, settings: SettingsDep
) -> User | None:
    """For endpoints that are public but richer when signed in (e.g. favorite flags)."""
    if credentials is None:
        return None
    return await get_current_user(credentials, session, settings)


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_roles(
    *roles: UserRole,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Dependency factory restricting an endpoint to the given roles (admins always pass)."""
    allowed = {*roles, UserRole.ADMIN}

    async def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise forbidden()
        return user

    return dependency


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def client_ip(request: Request, settings: SettingsDep) -> str | None:
    """The caller's IP, used for rate limiting.

    X-Forwarded-For is only honoured when TRUST_PROXY_HEADERS is on; otherwise any client
    could set it and slip past per-IP limits.
    """
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip() or None
    return request.client.host if request.client else None


ClientIp = Annotated[str | None, Depends(client_ip)]
