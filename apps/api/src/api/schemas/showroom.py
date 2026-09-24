import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.core.normalize import normalize_digits
from api.models.enums import ShowroomStaffRole, SubscriptionTier
from api.schemas.user import PublicUserOut

CR_NUMBER_LENGTH = 10


class ShowroomCreate(BaseModel):
    name_ar: str = Field(min_length=2, max_length=160)
    name_en: str | None = Field(default=None, max_length=160)
    commercial_registration_number: str = Field(min_length=6, max_length=20)
    city_id: uuid.UUID

    @field_validator("commercial_registration_number")
    @classmethod
    def _normalize_cr(cls, value: str) -> str:
        digits = normalize_digits(value).strip()
        if not digits.isdigit() or len(digits) != CR_NUMBER_LENGTH:
            raise ValueError(f"must be {CR_NUMBER_LENGTH} digits")
        return digits


class ShowroomUpdate(BaseModel):
    name_ar: str | None = Field(default=None, min_length=2, max_length=160)
    name_en: str | None = Field(default=None, max_length=160)
    city_id: uuid.UUID | None = None


class ShowroomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name_ar: str
    name_en: str | None
    city_id: uuid.UUID
    verified: bool
    subscription_tier: SubscriptionTier


class ShowroomStaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: ShowroomStaffRole
    user: PublicUserOut


class ShowroomStaffAdd(BaseModel):
    phone: str = Field(min_length=6, max_length=20)
    role: ShowroomStaffRole = ShowroomStaffRole.AGENT
