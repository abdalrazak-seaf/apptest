"""Showrooms (معارض): registration, details, and staff management."""

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from api.core.deps import AdminUser, CurrentUser, SessionDep
from api.core.errors import conflict, forbidden, not_found
from api.core.phone import normalize_saudi_phone
from api.models.enums import ShowroomStaffRole, UserRole
from api.models.geo import City
from api.models.showroom import Showroom, ShowroomStaff
from api.models.user import User
from api.schemas.common import Ack, ErrorResponse
from api.schemas.showroom import (
    ShowroomCreate,
    ShowroomOut,
    ShowroomStaffAdd,
    ShowroomStaffOut,
    ShowroomUpdate,
)
from api.services import showrooms as service

router = APIRouter(prefix="/showrooms", tags=["showrooms"])

ERRORS: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
}


async def _load(session: SessionDep, showroom_id: uuid.UUID) -> Showroom:
    showroom = await session.get(Showroom, showroom_id)
    if showroom is None:
        raise not_found("showroom_not_found")
    return showroom


async def _require_city(session: SessionDep, city_id: uuid.UUID) -> None:
    if await session.get(City, city_id) is None:
        raise not_found("city_not_found")


@router.post(
    "",
    name="create_showroom",
    response_model=ShowroomOut,
    status_code=status.HTTP_201_CREATED,
    responses={**ERRORS, 409: {"model": ErrorResponse}},
    summary="Register a showroom (the creator becomes its owner)",
)
async def create_showroom(
    payload: ShowroomCreate, user: CurrentUser, session: SessionDep
) -> Showroom:
    await _require_city(session, payload.city_id)
    showroom = Showroom(
        name_ar=payload.name_ar,
        name_en=payload.name_en,
        commercial_registration_number=payload.commercial_registration_number,
        city_id=payload.city_id,
    )
    session.add(showroom)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise conflict("commercial_registration_taken") from exc

    session.add(
        ShowroomStaff(showroom_id=showroom.id, user_id=user.id, role=ShowroomStaffRole.OWNER)
    )
    # Running a showroom implies selling; buyers keep their role until they post.
    if user.role == UserRole.BUYER:
        user.role = UserRole.SHOWROOM_STAFF
    await session.commit()
    await session.refresh(showroom)
    return showroom


@router.get(
    "/{showroom_id}",
    name="get_showroom",
    response_model=ShowroomOut,
    responses={404: {"model": ErrorResponse}},
)
async def get_showroom(showroom_id: uuid.UUID, session: SessionDep) -> Showroom:
    return await _load(session, showroom_id)


@router.patch(
    "/{showroom_id}",
    name="update_showroom",
    response_model=ShowroomOut,
    responses=ERRORS,
)
async def update_showroom(
    showroom_id: uuid.UUID,
    payload: ShowroomUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> Showroom:
    showroom = await _load(session, showroom_id)
    if not await service.may_manage(session, showroom_id=showroom.id, user=user):
        raise forbidden()
    changes = payload.model_dump(exclude_unset=True)
    if "city_id" in changes and changes["city_id"] is not None:
        await _require_city(session, changes["city_id"])
    for field, value in changes.items():
        setattr(showroom, field, value)
    await session.commit()
    await session.refresh(showroom)
    return showroom


@router.get(
    "/{showroom_id}/staff",
    name="list_showroom_staff",
    response_model=list[ShowroomStaffOut],
    responses=ERRORS,
    summary="Staff list (visible to the showroom's own staff)",
)
async def list_showroom_staff(
    showroom_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[ShowroomStaff]:
    await _load(session, showroom_id)
    if not await service.is_staff(session, showroom_id=showroom_id, user=user):
        raise forbidden()
    rows = await session.execute(
        select(ShowroomStaff)
        .where(ShowroomStaff.showroom_id == showroom_id)
        .options(selectinload(ShowroomStaff.user))
        .order_by(ShowroomStaff.created_at)
    )
    return list(rows.scalars())


@router.post(
    "/{showroom_id}/staff",
    name="add_showroom_staff",
    response_model=ShowroomStaffOut,
    status_code=status.HTTP_201_CREATED,
    responses={**ERRORS, 409: {"model": ErrorResponse}},
    summary="Add a staff member by phone number",
)
async def add_showroom_staff(
    showroom_id: uuid.UUID,
    payload: ShowroomStaffAdd,
    user: CurrentUser,
    session: SessionDep,
) -> ShowroomStaff:
    await _load(session, showroom_id)
    if not await service.may_manage(session, showroom_id=showroom_id, user=user):
        raise forbidden()

    phone = normalize_saudi_phone(payload.phone)
    if phone is None:
        raise not_found("user_not_found")
    member = (
        await session.execute(select(User).where(User.phone == phone, User.is_active))
    ).scalar_one_or_none()
    if member is None:
        # The person must sign up first; we never create accounts on someone else's behalf.
        raise not_found("user_not_found")

    if await service.get_membership(session, showroom_id=showroom_id, user_id=member.id):
        raise conflict("already_staff")

    staff = ShowroomStaff(showroom_id=showroom_id, user_id=member.id, role=payload.role)
    session.add(staff)
    if member.role == UserRole.BUYER:
        member.role = UserRole.SHOWROOM_STAFF
    await session.commit()
    await session.refresh(staff, ["user"])
    return staff


@router.delete(
    "/{showroom_id}/staff/{staff_id}",
    name="remove_showroom_staff",
    response_model=Ack,
    responses={**ERRORS, 409: {"model": ErrorResponse}},
)
async def remove_showroom_staff(
    showroom_id: uuid.UUID,
    staff_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
) -> Ack:
    await _load(session, showroom_id)
    if not await service.may_manage(session, showroom_id=showroom_id, user=user):
        raise forbidden()

    staff = await session.get(ShowroomStaff, staff_id)
    if staff is None or staff.showroom_id != showroom_id:
        raise not_found("staff_not_found")

    if staff.role == ShowroomStaffRole.OWNER:
        owners = (
            (
                await session.execute(
                    select(ShowroomStaff).where(
                        ShowroomStaff.showroom_id == showroom_id,
                        ShowroomStaff.role == ShowroomStaffRole.OWNER,
                    )
                )
            )
            .scalars()
            .all()
        )
        if len(owners) <= 1:
            # A showroom without an owner could never be managed again.
            raise conflict("last_owner")

    await session.delete(staff)
    await session.commit()
    return Ack()


@router.post(
    "/{showroom_id}/verify",
    name="verify_showroom",
    response_model=ShowroomOut,
    responses=ERRORS,
    summary="Mark a showroom as verified (admin only)",
)
async def verify_showroom(
    showroom_id: uuid.UUID, _admin: AdminUser, session: SessionDep
) -> Showroom:
    showroom = await _load(session, showroom_id)
    showroom.verified = True
    await session.commit()
    await session.refresh(showroom)
    return showroom
