import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.core.normalize import parse_int
from api.models.enums import (
    BodyType,
    FuelType,
    ListingStatus,
    RegionalSpec,
    SellerType,
    StatusReasonCode,
    Transmission,
)

# Cars older than this are out of scope for the MVP's pricing and taxonomy.
MIN_YEAR = 1970
MAX_YEAR = 2100
MAX_MILEAGE_KM = 2_000_000
MAX_PRICE_SAR = 20_000_000


def _coerce_number(value: object) -> object:
    """Accept '٩٠٠٠٠' and '90,000' as well as 90000, so Arabic keyboards just work."""
    if isinstance(value, str):
        parsed = parse_int(value)
        if parsed is None:
            raise ValueError("must be a number")
        return parsed
    return value


class ListingBase(BaseModel):
    make_id: uuid.UUID
    model_id: uuid.UUID
    trim_id: uuid.UUID | None = None
    year: int = Field(ge=MIN_YEAR, le=MAX_YEAR)
    mileage_km: int = Field(ge=0, le=MAX_MILEAGE_KM)
    body_type: BodyType | None = None
    transmission: Transmission = Transmission.AUTOMATIC
    fuel_type: FuelType = FuelType.PETROL
    engine: str | None = Field(default=None, max_length=60)
    color_ar: str | None = Field(default=None, max_length=40)
    regional_spec: RegionalSpec = RegionalSpec.SAUDI
    accident_history_declared: bool = False
    service_history_declared: bool = False
    asking_price_sar: int = Field(gt=0, le=MAX_PRICE_SAR)
    negotiable: bool = True
    city_id: uuid.UUID
    description_ar: str | None = Field(default=None, max_length=4000)
    description_en: str | None = Field(default=None, max_length=4000)

    _numbers = field_validator("year", "mileage_km", "asking_price_sar", mode="before")(
        _coerce_number
    )


class ListingCreate(ListingBase):
    # Post on behalf of a showroom the seller belongs to.
    showroom_id: uuid.UUID | None = None
    # Private walk-away price; never returned to buyers.
    floor_price_sar: int | None = Field(default=None, gt=0, le=MAX_PRICE_SAR)

    _floor = field_validator("floor_price_sar", mode="before")(_coerce_number)


class ListingUpdate(BaseModel):
    """Every field optional; only what is sent changes."""

    trim_id: uuid.UUID | None = None
    year: int | None = Field(default=None, ge=MIN_YEAR, le=MAX_YEAR)
    mileage_km: int | None = Field(default=None, ge=0, le=MAX_MILEAGE_KM)
    body_type: BodyType | None = None
    transmission: Transmission | None = None
    fuel_type: FuelType | None = None
    engine: str | None = Field(default=None, max_length=60)
    color_ar: str | None = Field(default=None, max_length=40)
    regional_spec: RegionalSpec | None = None
    accident_history_declared: bool | None = None
    service_history_declared: bool | None = None
    asking_price_sar: int | None = Field(default=None, gt=0, le=MAX_PRICE_SAR)
    floor_price_sar: int | None = Field(default=None, gt=0, le=MAX_PRICE_SAR)
    negotiable: bool | None = None
    city_id: uuid.UUID | None = None
    description_ar: str | None = Field(default=None, max_length=4000)
    description_en: str | None = Field(default=None, max_length=4000)

    _numbers = field_validator(
        "year", "mileage_km", "asking_price_sar", "floor_price_sar", mode="before"
    )(_coerce_number)


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int
    # Signed and expiring; media is never served from a public bucket.
    url: str


class ListingSummary(BaseModel):
    """What a search result shows. Deliberately excludes the seller's private fields."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    make_id: uuid.UUID
    model_id: uuid.UUID
    trim_id: uuid.UUID | None
    year: int
    mileage_km: int
    asking_price_sar: int
    city_id: uuid.UUID
    status: ListingStatus
    seller_type: SellerType
    published_at: datetime | None
    cover_photo: PhotoOut | None = None


class ListingDetail(ListingSummary):
    body_type: BodyType | None
    transmission: Transmission
    fuel_type: FuelType
    engine: str | None
    color_ar: str | None
    regional_spec: RegionalSpec
    accident_history_declared: bool
    service_history_declared: bool
    negotiable: bool
    description_ar: str | None
    description_en: str | None
    seller_id: uuid.UUID
    showroom_id: uuid.UUID | None
    views_count: int
    sold_at: datetime | None
    created_at: datetime
    photos: list[PhotoOut] = []


class SellerListingDetail(ListingDetail):
    """The seller's own view: adds the private fields only they may see."""

    floor_price_sar: int | None
    final_price_sar: int | None
    status_reason_code: StatusReasonCode | None
    status_reason_note: str | None


class StatusEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: ListingStatus | None
    to_status: ListingStatus
    reason_code: StatusReasonCode | None
    note: str | None
    created_at: datetime


class MarkSoldIn(BaseModel):
    final_price_sar: int = Field(gt=0, le=MAX_PRICE_SAR)

    _price = field_validator("final_price_sar", mode="before")(_coerce_number)


class StatusChangeIn(BaseModel):
    """Seller-driven status change (hide or republish)."""

    status: ListingStatus


class ModerationIn(BaseModel):
    approve: bool
    # Required when rejecting: the seller is always told why.
    reason_code: StatusReasonCode | None = None
    note: str | None = Field(default=None, max_length=500)


class ListingPage(BaseModel):
    items: list[ListingSummary]
    total: int
    limit: int
    offset: int
