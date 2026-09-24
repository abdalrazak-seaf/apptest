"""Shared SQLAlchemy column types and mixins."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """created_at / updated_at maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def enum_column[E: StrEnum](enum_type: type[E], **kwargs: object) -> Mapped[E]:
    """A VARCHAR column with a CHECK constraint, loaded back as the enum member.

    `values_callable` stores the member *values* ("buyer"), not their names ("BUYER"),
    so the database is readable and matches what the API exposes.
    """
    return mapped_column(
        Enum(
            enum_type,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda e: [member.value for member in e],
        ),
        **kwargs,  # type: ignore[arg-type]
    )
