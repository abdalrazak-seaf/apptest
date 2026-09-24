import uuid

from pydantic import BaseModel, ConfigDict


class CityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name_ar: str
    name_en: str
    region_ar: str
    region_en: str
