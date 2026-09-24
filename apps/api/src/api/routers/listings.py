"""Car listings: posting, editing, photos, search, and the status lifecycle."""

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.core.deps import (
    AdminUser,
    CurrentUser,
    OptionalUser,
    SessionDep,
    StorageDep,
)
from api.core.errors import conflict, forbidden, not_found
from api.integrations.storage import StorageProvider
from api.models.enums import (
    BodyType,
    FuelType,
    ListingStatus,
    RegionalSpec,
    SellerType,
    Transmission,
)
from api.models.event import EventName
from api.models.geo import City
from api.models.listing import Listing, ListingPhoto
from api.models.taxonomy import Make, Trim, VehicleModel
from api.models.user import User
from api.schemas.common import Ack, ErrorResponse
from api.schemas.listing import (
    ListingCreate,
    ListingDetail,
    ListingPage,
    ListingSummary,
    ListingUpdate,
    MarkSoldIn,
    ModerationIn,
    PhotoOut,
    SellerListingDetail,
    StatusChangeIn,
    StatusEventOut,
)
from api.services import events
from api.services import listings as service
from api.services import photos as photo_service
from api.services.search import ListingFilters, SortOrder, build_count_query, build_search_query
from api.services.showrooms import get_membership

router = APIRouter(prefix="/listings", tags=["listings"])

ERRORS: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


async def _load(session: SessionDep, listing_id: uuid.UUID) -> Listing:
    listing = (
        await session.execute(
            select(Listing).where(Listing.id == listing_id).options(selectinload(Listing.photos))
        )
    ).scalar_one_or_none()
    if listing is None:
        raise not_found("listing_not_found")
    return listing


async def _require_manage(session: SessionDep, listing: Listing, user: User) -> None:
    if not await service.may_manage(session, listing=listing, user=user):
        raise forbidden()


async def _to_photos(storage: StorageProvider, photos: list[ListingPhoto]) -> list[PhotoOut]:
    urls = await photo_service.photo_urls(storage, photos)
    return [PhotoOut(id=photo.id, position=photo.position, url=urls[photo.id]) for photo in photos]


async def _summary(storage: StorageProvider, listing: Listing) -> ListingSummary:
    summary = ListingSummary.model_validate(listing)
    if listing.photos:
        summary.cover_photo = (await _to_photos(storage, listing.photos[:1]))[0]
    return summary


async def _detail(storage: StorageProvider, listing: Listing, *, private: bool) -> ListingDetail:
    """Build the response explicitly: photos need signed URLs the ORM rows do not carry."""
    model = SellerListingDetail if private else ListingDetail
    photos = await _to_photos(storage, listing.photos)
    fields = {
        name: getattr(listing, name)
        for name in model.model_fields
        if name not in {"photos", "cover_photo"}
    }
    return model(**fields, photos=photos, cover_photo=photos[0] if photos else None)


@router.get(
    "",
    name="search_listings",
    response_model=ListingPage,
    summary="Search active listings (no sign-in required)",
)
async def search_listings(
    session: SessionDep,
    storage: StorageDep,
    user: OptionalUser,
    q: Annotated[
        str | None, Query(max_length=200, description="Free text, Arabic or English")
    ] = None,
    make_id: uuid.UUID | None = None,
    model_id: uuid.UUID | None = None,
    trim_id: uuid.UUID | None = None,
    city_id: uuid.UUID | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    mileage_max: int | None = None,
    body_type: BodyType | None = None,
    transmission: Transmission | None = None,
    fuel_type: FuelType | None = None,
    regional_spec: RegionalSpec | None = None,
    seller_type: SellerType | None = None,
    accident_free: bool | None = None,
    sort: SortOrder = SortOrder.NEWEST,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListingPage:
    filters = ListingFilters(
        query=q,
        make_id=make_id,
        model_id=model_id,
        trim_id=trim_id,
        city_id=city_id,
        year_min=year_min,
        year_max=year_max,
        price_min=price_min,
        price_max=price_max,
        mileage_max=mileage_max,
        body_type=body_type,
        transmission=transmission,
        fuel_type=fuel_type,
        regional_spec=regional_spec,
        seller_type=seller_type,
        accident_free=accident_free,
        sort=sort,
    )
    total = (await session.execute(build_count_query(filters))).scalar_one()
    rows = (
        await session.execute(build_search_query(filters, limit=limit, offset=offset))
    ).scalars()
    items = [await _summary(storage, listing) for listing in rows]

    await events.record(
        session,
        EventName.LISTING_SEARCHED,
        user_id=user.id if user else None,
        has_query=bool(q),
        results=total,
    )
    await session.commit()
    return ListingPage(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "",
    name="create_listing",
    response_model=SellerListingDetail,
    status_code=status.HTTP_201_CREATED,
    responses=ERRORS,
    summary="Create a draft listing",
)
async def create_listing(
    payload: ListingCreate, user: CurrentUser, session: SessionDep, storage: StorageDep
) -> ListingDetail:
    make = await session.get(Make, payload.make_id)
    if make is None:
        raise not_found("make_not_found")
    model = await session.get(VehicleModel, payload.model_id)
    if model is None or model.make_id != make.id:
        raise not_found("model_not_found")
    if payload.trim_id is not None:
        trim = await session.get(Trim, payload.trim_id)
        if trim is None or trim.model_id != model.id:
            raise not_found("trim_not_found")
    if await session.get(City, payload.city_id) is None:
        raise not_found("city_not_found")

    seller_type = SellerType.PRIVATE
    if payload.showroom_id is not None:
        membership = await get_membership(session, showroom_id=payload.showroom_id, user_id=user.id)
        if membership is None:
            raise forbidden("not_showroom_staff")
        seller_type = SellerType.SHOWROOM

    listing = Listing(
        seller_id=user.id,
        seller_type=seller_type,
        **payload.model_dump(exclude={"showroom_id"}),
        showroom_id=payload.showroom_id,
    )
    listing.body_type = payload.body_type or model.body_type
    session.add(listing)
    await session.flush()

    listing.search_text = await service.build_search_text(session, listing)
    await service.transition(
        session,
        listing,
        to_status=ListingStatus.DRAFT,
        reason_code=None,
        actor=user,
    )
    await events.record(session, EventName.LISTING_CREATED, user_id=user.id, listing_id=listing.id)
    await session.commit()
    await session.refresh(listing, ["photos"])
    return await _detail(storage, listing, private=True)


@router.get(
    "/mine",
    name="list_my_listings",
    response_model=list[SellerListingDetail],
    responses={401: {"model": ErrorResponse}},
    summary="Your own listings, in any status",
)
async def list_my_listings(
    user: CurrentUser, session: SessionDep, storage: StorageDep
) -> list[ListingDetail]:
    rows = (
        await session.execute(
            select(Listing)
            .where(Listing.seller_id == user.id)
            .options(selectinload(Listing.photos))
            .order_by(Listing.created_at.desc())
        )
    ).scalars()
    return [await _detail(storage, listing, private=True) for listing in rows]


@router.get(
    "/moderation/queue",
    name="list_moderation_queue",
    response_model=list[SellerListingDetail],
    responses=ERRORS,
    summary="Listings awaiting review (admin only)",
)
async def list_moderation_queue(
    admin: AdminUser, session: SessionDep, storage: StorageDep
) -> list[ListingDetail]:
    rows = (
        await session.execute(
            select(Listing)
            .where(Listing.status == ListingStatus.PENDING_REVIEW)
            .options(selectinload(Listing.photos))
            .order_by(Listing.created_at)
        )
    ).scalars()
    return [await _detail(storage, listing, private=True) for listing in rows]


@router.get(
    "/{listing_id}",
    name="get_listing",
    response_model=ListingDetail,
    responses={404: {"model": ErrorResponse}},
    summary="Listing detail (private fields only for the seller)",
)
async def get_listing(
    listing_id: uuid.UUID,
    session: SessionDep,
    storage: StorageDep,
    user: OptionalUser,
) -> ListingDetail:
    listing = await _load(session, listing_id)
    if not service.is_visible_to(listing, user):
        # Don't reveal that a hidden listing exists.
        raise not_found("listing_not_found")

    owner_side = user is not None and await service.may_manage(session, listing=listing, user=user)
    if not owner_side:
        listing.views_count += 1
        await events.record(
            session,
            EventName.LISTING_VIEWED,
            user_id=user.id if user else None,
            listing_id=listing.id,
        )
        await session.commit()
    # Always the buyer-facing shape: private fields live on /manage below.
    return await _detail(storage, listing, private=False)


@router.get(
    "/{listing_id}/manage",
    name="get_my_listing",
    response_model=SellerListingDetail,
    responses=ERRORS,
    summary="The seller's own view, including the private floor price",
)
async def get_my_listing(
    listing_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    storage: StorageDep,
) -> ListingDetail:
    listing = await _load(session, listing_id)
    await _require_manage(session, listing, user)
    return await _detail(storage, listing, private=True)


@router.patch(
    "/{listing_id}",
    name="update_listing",
    response_model=SellerListingDetail,
    responses=ERRORS,
)
async def update_listing(
    listing_id: uuid.UUID,
    payload: ListingUpdate,
    user: CurrentUser,
    session: SessionDep,
    storage: StorageDep,
) -> ListingDetail:
    listing = await _load(session, listing_id)
    await _require_manage(session, listing, user)
    if listing.status not in service.EDITABLE_STATUSES:
        raise conflict("listing_not_editable")

    changes = payload.model_dump(exclude_unset=True)
    if changes.get("city_id") and await session.get(City, changes["city_id"]) is None:
        raise not_found("city_not_found")
    if changes.get("trim_id"):
        trim = await session.get(Trim, changes["trim_id"])
        if trim is None or trim.model_id != listing.model_id:
            raise not_found("trim_not_found")

    for field, value in changes.items():
        setattr(listing, field, value)
    listing.search_text = await service.build_search_text(session, listing)
    await session.commit()
    await session.refresh(listing, ["photos"])
    return await _detail(storage, listing, private=True)


@router.post(
    "/{listing_id}/photos",
    name="upload_listing_photo",
    response_model=PhotoOut,
    status_code=status.HTTP_201_CREATED,
    responses=ERRORS,
    summary="Upload one photo (JPEG, PNG or WebP)",
)
async def upload_listing_photo(
    listing_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    storage: StorageDep,
    file: Annotated[UploadFile, File(description="Image file, up to 8 MB")],
) -> PhotoOut:
    listing = await _load(session, listing_id)
    await _require_manage(session, listing, user)

    data = await file.read()
    photo = await photo_service.add_photo(
        session, storage, listing=listing, data=data, filename=file.filename or "photo"
    )
    await session.commit()
    urls = await photo_service.photo_urls(storage, [photo])
    return PhotoOut(id=photo.id, position=photo.position, url=urls[photo.id])


@router.delete(
    "/{listing_id}/photos/{photo_id}",
    name="delete_listing_photo",
    response_model=Ack,
    responses=ERRORS,
)
async def delete_listing_photo(
    listing_id: uuid.UUID,
    photo_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
) -> Ack:
    listing = await _load(session, listing_id)
    await _require_manage(session, listing, user)

    photo = await session.get(ListingPhoto, photo_id)
    if photo is None or photo.listing_id != listing.id:
        raise not_found("photo_not_found")
    await session.delete(photo)
    await session.commit()
    return Ack()


@router.post(
    "/{listing_id}/publish",
    name="publish_listing",
    response_model=SellerListingDetail,
    responses=ERRORS,
    summary="Submit a draft for review",
)
async def publish_listing(
    listing_id: uuid.UUID, user: CurrentUser, session: SessionDep, storage: StorageDep
) -> ListingDetail:
    listing = await _load(session, listing_id)
    await _require_manage(session, listing, user)
    await service.submit_for_review(session, listing, actor=user)
    await session.commit()
    await session.refresh(listing, ["photos"])
    return await _detail(storage, listing, private=True)


@router.put(
    "/{listing_id}/status",
    name="set_listing_status",
    response_model=SellerListingDetail,
    responses=ERRORS,
    summary="Hide or republish your listing",
)
async def set_listing_status(
    listing_id: uuid.UUID,
    payload: StatusChangeIn,
    user: CurrentUser,
    session: SessionDep,
    storage: StorageDep,
) -> ListingDetail:
    listing = await _load(session, listing_id)
    await _require_manage(session, listing, user)
    await service.seller_set_status(session, listing, to_status=payload.status, actor=user)
    await session.commit()
    await session.refresh(listing, ["photos"])
    return await _detail(storage, listing, private=True)


@router.post(
    "/{listing_id}/sold",
    name="mark_listing_sold",
    response_model=SellerListingDetail,
    responses=ERRORS,
    summary="Mark as sold and record the final price",
)
async def mark_listing_sold(
    listing_id: uuid.UUID,
    payload: MarkSoldIn,
    user: CurrentUser,
    session: SessionDep,
    storage: StorageDep,
) -> ListingDetail:
    listing = await _load(session, listing_id)
    await _require_manage(session, listing, user)
    await service.mark_sold(session, listing, final_price_sar=payload.final_price_sar, actor=user)
    await events.record(
        session,
        EventName.LISTING_MARKED_SOLD,
        user_id=user.id,
        listing_id=listing.id,
        final_price_sar=payload.final_price_sar,
        asking_price_sar=listing.asking_price_sar,
    )
    await session.commit()
    await session.refresh(listing, ["photos"])
    return await _detail(storage, listing, private=True)


@router.get(
    "/{listing_id}/status-history",
    name="get_listing_status_history",
    response_model=list[StatusEventOut],
    responses=ERRORS,
    summary="Why this listing is in its current status",
)
async def get_listing_status_history(
    listing_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[StatusEventOut]:
    listing = await _load(session, listing_id)
    await _require_manage(session, listing, user)
    history = await service.load_status_history(session, listing.id)
    return [StatusEventOut.model_validate(event) for event in history]


@router.post(
    "/{listing_id}/moderate",
    name="moderate_listing",
    response_model=SellerListingDetail,
    responses=ERRORS,
    summary="Approve or reject a listing (admin only)",
)
async def moderate_listing(
    listing_id: uuid.UUID,
    payload: ModerationIn,
    admin: AdminUser,
    session: SessionDep,
    storage: StorageDep,
) -> ListingDetail:
    listing = await _load(session, listing_id)
    await service.moderate(
        session,
        listing,
        approve=payload.approve,
        reason_code=payload.reason_code,
        note=payload.note,
        actor=admin,
    )
    if payload.approve:
        await events.record(
            session,
            EventName.LISTING_PUBLISHED,
            user_id=listing.seller_id,
            listing_id=listing.id,
        )
    await session.commit()
    await session.refresh(listing, ["photos"])
    return await _detail(storage, listing, private=True)
