"""Vehicle taxonomy: make -> model -> trim, with Arabic search aliases."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.db import Base
from api.core.models import TimestampMixin, enum_column, uuid_pk
from api.models.enums import BodyType

# Aliases are stored already normalized (see api.core.normalize.normalize_arabic) so that
# a buyer typing "جمس" or "لاندكروزر" matches without extra processing at query time.
AliasList = ARRAY(String(120))


class Make(TimestampMixin, Base):
    __tablename__ = "makes"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name_ar: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    aliases: Mapped[list[str]] = mapped_column(AliasList, default=list)
    # Lower sorts first: the makes that dominate the Saudi market lead the picker.
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    models: Mapped[list["VehicleModel"]] = relationship(
        back_populates="make", cascade="all, delete-orphan"
    )


class VehicleModel(TimestampMixin, Base):
    """A model within a make. Named `VehicleModel` to avoid clashing with Pydantic models."""

    __tablename__ = "vehicle_models"
    __table_args__ = (UniqueConstraint("make_id", "slug", name="make_slug"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    make_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("makes.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(64), index=True)
    name_ar: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    aliases: Mapped[list[str]] = mapped_column(AliasList, default=list)
    body_type: Mapped[BodyType | None] = enum_column(BodyType, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    make: Mapped[Make] = relationship(back_populates="models")
    trims: Mapped[list["Trim"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class Trim(TimestampMixin, Base):
    __tablename__ = "trims"
    __table_args__ = (UniqueConstraint("model_id", "slug", name="model_slug"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicle_models.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(64), index=True)
    name_ar: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    aliases: Mapped[list[str]] = mapped_column(AliasList, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    model: Mapped[VehicleModel] = relationship(back_populates="trims")
