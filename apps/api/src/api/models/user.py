"""Users and the records backing phone-OTP login."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.db import Base
from api.core.models import TimestampMixin, enum_column, uuid_pk
from api.models.enums import Language, UserRole


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    # E.164, e.g. +966501234567. Never exposed publicly (contact goes through chat).
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_language: Mapped[Language] = enum_column(Language, default=Language.AR)
    role: Mapped[UserRole] = enum_column(UserRole, default=UserRole.BUYER, index=True)
    city_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cities.id", ondelete="SET NULL"), nullable=True
    )
    # Set by an identity provider (Nafath) in a later phase; never self-asserted.
    identity_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    identity_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Deactivated accounts keep their rows (listings, reviews) but cannot log in.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class OtpRequest(TimestampMixin, Base):
    """A login code sent to a phone. The code itself is only ever stored hashed."""

    __tablename__ = "otp_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshToken(TimestampMixin, Base):
    """One row per issued refresh token, stored hashed, rotated on every use.

    `replaced_by_id` lets us detect replay of an already-rotated token: when that happens the
    whole chain is revoked, because either the token leaked or a client is misbehaving.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")
