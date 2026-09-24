"""Car listings, their photos, and the audit trail behind every status change."""

import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.db import Base
from api.core.models import TimestampMixin, enum_column, uuid_pk
from api.models.enums import (
    BodyType,
    FuelType,
    ListingStatus,
    RegionalSpec,
    SellerType,
    StatusReasonCode,
    Transmission,
)

# A listing must show at least this many photos before it can be published.
MIN_PHOTOS_TO_PUBLISH = 4
MAX_PHOTOS = 20


class Listing(TimestampMixin, Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("asking_price_sar > 0", name="asking_price_positive"),
        CheckConstraint(
            "floor_price_sar IS NULL OR floor_price_sar > 0", name="floor_price_positive"
        ),
        CheckConstraint("mileage_km >= 0", name="mileage_non_negative"),
        # Browsing is almost always "active listings in a city, newest first".
        Index("ix_listings_status_city_created", "status", "city_id", "created_at"),
        Index("ix_listings_status_price", "status", "asking_price_sar"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()

    # --- Who is selling -------------------------------------------------
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Set when the seller posts on behalf of a showroom they belong to.
    showroom_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("showrooms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    seller_type: Mapped[SellerType] = enum_column(SellerType, default=SellerType.PRIVATE)

    # --- The car --------------------------------------------------------
    make_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("makes.id", ondelete="RESTRICT"))
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicle_models.id", ondelete="RESTRICT")
    )
    trim_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trims.id", ondelete="SET NULL"), nullable=True
    )
    year: Mapped[int] = mapped_column(Integer)
    mileage_km: Mapped[int] = mapped_column(Integer)
    body_type: Mapped[BodyType | None] = enum_column(BodyType, nullable=True)
    transmission: Mapped[Transmission] = enum_column(Transmission, default=Transmission.AUTOMATIC)
    fuel_type: Mapped[FuelType] = enum_column(FuelType, default=FuelType.PETROL)
    engine: Mapped[str | None] = mapped_column(String(60), nullable=True)
    color_ar: Mapped[str | None] = mapped_column(String(40), nullable=True)
    regional_spec: Mapped[RegionalSpec] = enum_column(RegionalSpec, default=RegionalSpec.SAUDI)
    # Declared by the seller, never asserted by us.
    accident_history_declared: Mapped[bool] = mapped_column(Boolean, default=False)
    service_history_declared: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Price ----------------------------------------------------------
    asking_price_sar: Mapped[int] = mapped_column(Integer)
    # The seller's private walk-away price. NEVER returned by a buyer-facing endpoint;
    # the Deal Agent negotiates against it in Phase 4.
    floor_price_sar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    negotiable: Mapped[bool] = mapped_column(Boolean, default=True)

    # --- Where ----------------------------------------------------------
    city_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cities.id", ondelete="RESTRICT"), index=True
    )
    # Approximate point shown on the map; buyers never get an exact address.
    location: Mapped[object | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )

    # --- Text -----------------------------------------------------------
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Arabic-normalized haystack (make, model, trim, aliases, description) kept in sync by
    # the listing service, so search matches "جمس" and "لاندكروزر" without extra joins.
    search_text: Mapped[str] = mapped_column(Text, default="")

    # --- Lifecycle ------------------------------------------------------
    status: Mapped[ListingStatus] = enum_column(
        ListingStatus, default=ListingStatus.DRAFT, index=True
    )
    # Always set for a non-active status, so the seller is never left guessing.
    status_reason_code: Mapped[StatusReasonCode | None] = enum_column(
        StatusReasonCode, nullable=True
    )
    # Optional free text from a moderator, shown to the seller alongside the code.
    status_reason_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Captured on "mark as sold"; feeds the Fair-Price Engine in Phase 3.
    final_price_sar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0)

    photos: Mapped[list["ListingPhoto"]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="ListingPhoto.position",
    )
    status_events: Mapped[list["ListingStatusEvent"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )


class ListingPhoto(TimestampMixin, Base):
    __tablename__ = "listing_photos"
    __table_args__ = (UniqueConstraint("listing_id", "position", name="listing_position"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(256))
    content_type: Mapped[str] = mapped_column(String(40))
    size_bytes: Mapped[int] = mapped_column(Integer)
    # 0 is the cover photo shown in search results.
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Perceptual hash for duplicate detection (Phase 5); computed on upload.
    perceptual_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    listing: Mapped[Listing] = relationship(back_populates="photos")


class ListingStatusEvent(TimestampMixin, Base):
    """One row per status change, so the seller can see exactly what happened and why."""

    __tablename__ = "listing_status_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[ListingStatus | None] = enum_column(ListingStatus, nullable=True)
    to_status: Mapped[ListingStatus] = enum_column(ListingStatus)
    reason_code: Mapped[StatusReasonCode | None] = enum_column(StatusReasonCode, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Null when the change was automatic (e.g. expiry).
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    listing: Mapped[Listing] = relationship(back_populates="status_events")
