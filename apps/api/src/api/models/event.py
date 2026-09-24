"""Analytics events behind the north-star metrics (brief §1).

Rows are append-only and deliberately thin: a name, who/what it refers to, and a small
JSON payload. Reporting queries live in Phase 7's admin dashboard.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.core.db import Base
from api.core.models import TimestampMixin, uuid_pk


class EventName(StrEnum):
    LISTING_CREATED = "listing_created"
    LISTING_PUBLISHED = "listing_published"
    LISTING_VIEWED = "listing_viewed"
    LISTING_SEARCHED = "listing_searched"
    LISTING_MARKED_SOLD = "listing_marked_sold"
    CONTACT_STARTED = "contact_started"
    QUALIFIED_INQUIRY = "qualified_inquiry"
    VIEWING_BOOKED = "viewing_booked"


class Event(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_name_created", "name", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[EventName] = mapped_column(String(40))
    # Null for anonymous browsing, which is allowed without signing up.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
