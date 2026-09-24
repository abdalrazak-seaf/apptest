import uuid

from pydantic import BaseModel, ConfigDict

from api.models.enums import BodyType


class MakeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name_ar: str
    name_en: str


class VehicleModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    make_id: uuid.UUID
    slug: str
    name_ar: str
    name_en: str
    body_type: BodyType | None = None


class TrimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_id: uuid.UUID
    slug: str
    name_ar: str
    name_en: str
