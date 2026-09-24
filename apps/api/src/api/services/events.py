"""Recording analytics events (brief §5, north-star metrics)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.models.event import Event, EventName


async def record(
    session: AsyncSession,
    name: EventName,
    *,
    user_id: uuid.UUID | None = None,
    listing_id: uuid.UUID | None = None,
    **properties: Any,
) -> None:
    """Append one event. Never raises into the request path's happy case."""
    session.add(Event(name=name, user_id=user_id, listing_id=listing_id, properties=properties))
