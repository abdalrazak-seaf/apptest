"""Saudi cities. Seeded from `api.scripts.seed`; never user-created."""

import uuid

from geoalchemy2 import Geography
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from api.core.db import Base
from api.core.models import TimestampMixin, uuid_pk


class City(TimestampMixin, Base):
    __tablename__ = "cities"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Stable identifier used by clients and seeds, e.g. "riyadh".
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name_ar: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    region_ar: Mapped[str] = mapped_column(String(120))
    region_en: Mapped[str] = mapped_column(String(120))
    # City centre; listings carry their own approximate location.
    location: Mapped[object] = mapped_column(Geography(geometry_type="POINT", srid=4326))
    # Controls ordering in pickers (largest markets first).
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
