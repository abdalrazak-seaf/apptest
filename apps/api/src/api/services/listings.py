"""Listing lifecycle: what may change, who may change it, and why.

Every status change goes through `transition`, which records a ListingStatusEvent, so the
seller can always see what happened and the reason behind it.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.errors import conflict, forbidden
from api.core.normalize import normalize_arabic
from api.models.enums import ListingStatus, StatusReasonCode, UserRole
from api.models.listing import MIN_PHOTOS_TO_PUBLISH, Listing, ListingStatusEvent
from api.models.taxonomy import Make, Trim, VehicleModel
from api.models.user import User
from api.services.showrooms import get_membership

logger = logging.getLogger(__name__)

# Statuses a buyer may see. Everything else belongs to the seller and moderators.
PUBLIC_STATUSES = (ListingStatus.ACTIVE, ListingStatus.SOLD)

# Which transitions a seller may ask for, and the reason recorded for each.
SELLER_TRANSITIONS: dict[tuple[ListingStatus, ListingStatus], StatusReasonCode] = {
    (ListingStatus.DRAFT, ListingStatus.PENDING_REVIEW): StatusReasonCode.AWAITING_REVIEW,
    (ListingStatus.ACTIVE, ListingStatus.HIDDEN): StatusReasonCode.SELLER_HID,
    (ListingStatus.HIDDEN, ListingStatus.ACTIVE): StatusReasonCode.SELLER_REPUBLISHED,
    (ListingStatus.REJECTED, ListingStatus.PENDING_REVIEW): StatusReasonCode.AWAITING_REVIEW,
    (ListingStatus.EXPIRED, ListingStatus.PENDING_REVIEW): StatusReasonCode.AWAITING_REVIEW,
}

# A listing may only be edited while the seller still controls it.
EDITABLE_STATUSES = (
    ListingStatus.DRAFT,
    ListingStatus.PENDING_REVIEW,
    ListingStatus.ACTIVE,
    ListingStatus.HIDDEN,
    ListingStatus.REJECTED,
    ListingStatus.EXPIRED,
)


def _now() -> datetime:
    return datetime.now(UTC)


async def may_manage(session: AsyncSession, *, listing: Listing, user: User) -> bool:
    """The seller, their showroom colleagues, and admins may manage a listing."""
    if user.role == UserRole.ADMIN or listing.seller_id == user.id:
        return True
    if listing.showroom_id is None:
        return False
    membership = await get_membership(session, showroom_id=listing.showroom_id, user_id=user.id)
    return membership is not None


def is_visible_to(listing: Listing, user: User | None) -> bool:
    """Buyers see active and sold listings; everything else only the owner side sees."""
    if listing.status in PUBLIC_STATUSES:
        return True
    if user is None:
        return False
    return user.role == UserRole.ADMIN or listing.seller_id == user.id


async def build_search_text(session: AsyncSession, listing: Listing) -> str:
    """Normalized haystack so Arabic spellings and aliases all match one another."""
    make = await session.get(Make, listing.make_id)
    model = await session.get(VehicleModel, listing.model_id)
    trim = await session.get(Trim, listing.trim_id) if listing.trim_id else None

    parts: list[str] = [str(listing.year)]
    for entity in (make, model, trim):
        if entity is None:
            continue
        parts.extend([entity.name_ar, entity.name_en, *entity.aliases])
    parts.extend(filter(None, [listing.description_ar, listing.description_en, listing.color_ar]))
    return normalize_arabic(" ".join(parts))


async def transition(
    session: AsyncSession,
    listing: Listing,
    *,
    to_status: ListingStatus,
    reason_code: StatusReasonCode | None,
    actor: User | None,
    note: str | None = None,
) -> Listing:
    """Move a listing to a new status and record why."""
    from_status = listing.status
    listing.status = to_status
    # Active listings need no explanation; every other status must carry one.
    listing.status_reason_code = None if to_status == ListingStatus.ACTIVE else reason_code
    listing.status_reason_note = None if to_status == ListingStatus.ACTIVE else note

    if to_status == ListingStatus.ACTIVE and listing.published_at is None:
        listing.published_at = _now()

    session.add(
        ListingStatusEvent(
            listing_id=listing.id,
            from_status=from_status,
            to_status=to_status,
            reason_code=reason_code,
            note=note,
            actor_id=actor.id if actor else None,
        )
    )
    logger.info(
        "listing_status_changed",
        extra={
            "listing_id": str(listing.id),
            "from_status": from_status,
            "to_status": to_status,
            "reason_code": reason_code,
        },
    )
    return listing


async def submit_for_review(session: AsyncSession, listing: Listing, *, actor: User) -> Listing:
    """Seller publishes: we check the listing is complete, then queue it for review."""
    photo_count = len(listing.photos)
    if photo_count < MIN_PHOTOS_TO_PUBLISH:
        raise conflict("not_enough_photos")

    key = (listing.status, ListingStatus.PENDING_REVIEW)
    if key not in SELLER_TRANSITIONS:
        raise conflict("invalid_status_transition")

    return await transition(
        session,
        listing,
        to_status=ListingStatus.PENDING_REVIEW,
        reason_code=StatusReasonCode.AWAITING_REVIEW,
        actor=actor,
    )


async def seller_set_status(
    session: AsyncSession, listing: Listing, *, to_status: ListingStatus, actor: User
) -> Listing:
    reason = SELLER_TRANSITIONS.get((listing.status, to_status))
    if reason is None:
        raise conflict("invalid_status_transition")
    return await transition(session, listing, to_status=to_status, reason_code=reason, actor=actor)


async def mark_sold(
    session: AsyncSession, listing: Listing, *, final_price_sar: int, actor: User
) -> Listing:
    if listing.status == ListingStatus.SOLD:
        raise conflict("already_sold")
    if listing.status not in (ListingStatus.ACTIVE, ListingStatus.HIDDEN):
        raise conflict("invalid_status_transition")

    listing.sold_at = _now()
    listing.final_price_sar = final_price_sar
    return await transition(
        session,
        listing,
        to_status=ListingStatus.SOLD,
        reason_code=StatusReasonCode.SELLER_SOLD,
        actor=actor,
    )


async def moderate(
    session: AsyncSession,
    listing: Listing,
    *,
    approve: bool,
    reason_code: StatusReasonCode | None,
    note: str | None,
    actor: User,
) -> Listing:
    """Admin decision on a listing. A rejection must say why."""
    if actor.role != UserRole.ADMIN:
        raise forbidden()
    if approve:
        return await transition(
            session,
            listing,
            to_status=ListingStatus.ACTIVE,
            reason_code=StatusReasonCode.APPROVED,
            actor=actor,
        )
    if reason_code is None:
        raise conflict("reason_code_required")
    return await transition(
        session,
        listing,
        to_status=ListingStatus.REJECTED,
        reason_code=reason_code,
        actor=actor,
        note=note,
    )


async def load_status_history(
    session: AsyncSession, listing_id: uuid.UUID
) -> list[ListingStatusEvent]:
    rows = await session.execute(
        select(ListingStatusEvent)
        .where(ListingStatusEvent.listing_id == listing_id)
        .order_by(ListingStatusEvent.created_at)
    )
    return list(rows.scalars())
