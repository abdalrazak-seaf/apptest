"""Phone-OTP login, JWT issuance and refresh-token rotation."""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.core import ratelimit
from api.core.config import Settings
from api.core.errors import forbidden, too_many_requests, unauthorized
from api.core.phone import mask_phone, normalize_saudi_phone
from api.core.security import (
    constant_time_equals,
    create_access_token,
    generate_otp_code,
    generate_refresh_token,
    hash_otp_code,
    hash_refresh_token,
)
from api.integrations.sms import SmsProvider
from api.models.enums import Language, UserRole
from api.models.user import OtpRequest, RefreshToken, User

logger = logging.getLogger(__name__)

# Sent to the buyer/seller; the client never needs to parse it.
OTP_MESSAGE_AR = "رمز الدخول إلى {app}: {code}\nصالح لمدة {minutes} دقائق. لا تشاركه مع أحد."
OTP_MESSAGE_EN = "Your {app} login code: {code}\nValid for {minutes} minutes. Do not share it."


class InvalidPhoneError(Exception):
    """The phone number is not a Saudi mobile number."""


@dataclass(frozen=True)
class OtpChallenge:
    phone: str
    expires_in_s: int
    # Only populated when OTP_EXPOSE_CODE is on (local development).
    debug_code: str | None


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in_s: int
    user: User


def _now() -> datetime:
    return datetime.now(UTC)


async def request_otp(
    session: AsyncSession,
    redis: Redis,
    sms: SmsProvider,
    settings: Settings,
    *,
    raw_phone: str,
    client_ip: str | None,
    language: Language = Language.AR,
) -> OtpChallenge:
    """Send a login code, rate-limited per phone and per client IP."""
    phone = normalize_saudi_phone(raw_phone)
    if phone is None:
        raise InvalidPhoneError(raw_phone)

    limits = [f"otp:phone:{phone}"]
    if client_ip:
        limits.append(f"otp:ip:{client_ip}")
    for key in limits:
        result = await ratelimit.hit(
            redis, key, limit=settings.otp_requests_per_window, window_s=settings.otp_window_s
        )
        if not result.allowed:
            raise too_many_requests("otp_rate_limited", retry_after_s=result.retry_after_s)

    # Any earlier code for this phone stops working as soon as a new one is sent.
    await session.execute(
        update(OtpRequest)
        .where(OtpRequest.phone == phone, OtpRequest.consumed_at.is_(None))
        .values(consumed_at=_now())
    )

    code = generate_otp_code(settings.otp_length)
    session.add(
        OtpRequest(
            phone=phone,
            code_hash=hash_otp_code(settings, phone=phone, code=code),
            expires_at=_now() + timedelta(seconds=settings.otp_ttl_s),
        )
    )
    await session.commit()

    template = OTP_MESSAGE_AR if language is Language.AR else OTP_MESSAGE_EN
    await sms.send(
        phone,
        template.format(app=settings.app_name, code=code, minutes=max(settings.otp_ttl_s // 60, 1)),
    )
    logger.info("otp_requested", extra={"phone": mask_phone(phone)})

    return OtpChallenge(
        phone=phone,
        expires_in_s=settings.otp_ttl_s,
        debug_code=code if settings.otp_expose_code else None,
    )


async def verify_otp(
    session: AsyncSession,
    redis: Redis,
    settings: Settings,
    *,
    raw_phone: str,
    code: str,
    user_agent: str | None = None,
) -> TokenPair:
    """Exchange a valid code for tokens, creating the user on first login."""
    phone = normalize_saudi_phone(raw_phone)
    if phone is None:
        raise InvalidPhoneError(raw_phone)

    otp = (
        await session.execute(
            select(OtpRequest)
            .where(OtpRequest.phone == phone, OtpRequest.consumed_at.is_(None))
            .order_by(OtpRequest.created_at.desc())
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()

    if otp is None or otp.expires_at <= _now():
        raise unauthorized("otp_invalid")

    if otp.attempts >= settings.otp_max_attempts:
        otp.consumed_at = _now()
        await session.commit()
        raise unauthorized("otp_invalid")

    expected = hash_otp_code(settings, phone=phone, code=code.strip())
    if not constant_time_equals(otp.code_hash, expected):
        otp.attempts += 1
        await session.commit()
        raise unauthorized("otp_invalid")

    otp.consumed_at = _now()

    user = (await session.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if user is None:
        user = User(phone=phone, role=UserRole.BUYER)
        session.add(user)
        await session.flush()
    elif not user.is_active:
        await session.commit()
        raise forbidden("account_disabled")

    user.last_login_at = _now()
    pair = await _issue_tokens(session, settings, user=user, user_agent=user_agent)
    await session.commit()

    # A successful login clears the per-phone throttle.
    await ratelimit.reset(redis, f"otp:phone:{phone}")
    logger.info("login_succeeded", extra={"user_id": str(user.id)})
    return pair


async def refresh_tokens(
    session: AsyncSession,
    settings: Settings,
    *,
    refresh_token: str,
    user_agent: str | None = None,
) -> TokenPair:
    """Rotate a refresh token. Reusing an already-rotated token revokes the whole family."""
    token_hash = hash_refresh_token(refresh_token)
    stored = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        )
    ).scalar_one_or_none()

    if stored is None:
        raise unauthorized("refresh_token_invalid")

    if stored.replaced_by_id is not None:
        # This token was already rotated, so a second use means it leaked (or a client is
        # replaying it). Sign the user out everywhere rather than trust either holder.
        await revoke_all_for_user(session, stored.user_id)
        await session.commit()
        logger.warning("refresh_token_reuse_detected", extra={"user_id": str(stored.user_id)})
        raise unauthorized("refresh_token_invalid")

    if stored.revoked_at is not None:
        # Explicitly logged out: reject this token only, leaving the user's other devices alone.
        raise unauthorized("refresh_token_invalid")

    if stored.expires_at <= _now():
        raise unauthorized("refresh_token_invalid")

    user = await session.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise unauthorized("refresh_token_invalid")

    pair = await _issue_tokens(session, settings, user=user, user_agent=user_agent)
    stored.revoked_at = _now()
    stored.replaced_by_id = (
        await session.execute(
            select(RefreshToken.id).where(
                RefreshToken.token_hash == hash_refresh_token(pair.refresh_token)
            )
        )
    ).scalar_one()
    await session.commit()
    return pair


async def revoke_refresh_token(session: AsyncSession, *, refresh_token: str) -> None:
    """Log out one device. Unknown or already-revoked tokens are a no-op."""
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == hash_refresh_token(refresh_token),
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=_now())
    )
    await session.commit()


async def revoke_all_for_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


async def _issue_tokens(
    session: AsyncSession, settings: Settings, *, user: User, user_agent: str | None
) -> TokenPair:
    refresh_token = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=_now() + timedelta(seconds=settings.refresh_token_ttl_s),
            user_agent=(user_agent or "")[:200] or None,
        )
    )
    await session.flush()
    return TokenPair(
        access_token=create_access_token(settings, user_id=user.id, role=user.role),
        refresh_token=refresh_token,
        expires_in_s=settings.access_token_ttl_s,
        user=user,
    )
