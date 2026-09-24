import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from api.models.enums import Language, UserRole


class UserOut(BaseModel):
    """The signed-in user's own profile. Phone is only ever returned to that user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str
    name: str | None
    preferred_language: Language
    role: UserRole
    city_id: uuid.UUID | None
    identity_verified: bool
    created_at: datetime


class PublicUserOut(BaseModel):
    """What other users may see. Never includes the phone number."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    identity_verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    preferred_language: Language | None = None
    city_id: uuid.UUID | None = None


class RoleUpdate(BaseModel):
    """A buyer can become a seller themselves; admin roles are granted by an admin only."""

    role: UserRole
