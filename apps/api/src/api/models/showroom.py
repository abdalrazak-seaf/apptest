"""Showrooms (معارض) and their staff."""

import uuid

from geoalchemy2 import Geography
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.db import Base
from api.core.models import TimestampMixin, enum_column, uuid_pk
from api.models.enums import ShowroomStaffRole, SubscriptionTier
from api.models.user import User


class Showroom(TimestampMixin, Base):
    __tablename__ = "showrooms"

    id: Mapped[uuid.UUID] = uuid_pk()
    name_ar: Mapped[str] = mapped_column(String(160))
    name_en: Mapped[str | None] = mapped_column(String(160), nullable=True)
    # Saudi commercial registration ("السجل التجاري"), 10 digits. Verified by an admin.
    commercial_registration_number: Mapped[str] = mapped_column(String(20), unique=True)
    city_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"))
    location: Mapped[object | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )
    logo_storage_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_tier: Mapped[SubscriptionTier] = enum_column(
        SubscriptionTier, default=SubscriptionTier.FREE
    )

    staff: Mapped[list["ShowroomStaff"]] = relationship(
        back_populates="showroom", cascade="all, delete-orphan"
    )


class ShowroomStaff(TimestampMixin, Base):
    __tablename__ = "showroom_staff"
    __table_args__ = (UniqueConstraint("showroom_id", "user_id", name="showroom_user"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    showroom_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("showrooms.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[ShowroomStaffRole] = enum_column(
        ShowroomStaffRole, default=ShowroomStaffRole.AGENT
    )

    showroom: Mapped[Showroom] = relationship(back_populates="staff")
    user: Mapped[User] = relationship()
