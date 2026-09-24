"""The signed-in user's own profile, plus public profiles."""

import uuid
from typing import Any

from fastapi import APIRouter

from api.core.deps import CurrentUser, SessionDep
from api.core.errors import forbidden, not_found
from api.models.enums import UserRole
from api.models.user import User
from api.schemas.common import Ack, ErrorResponse
from api.schemas.user import PublicUserOut, RoleUpdate, UserOut, UserUpdate
from api.services import users as users_service

router = APIRouter(tags=["users"])

# Roles a user may switch to on their own. Admin and showroom staff are granted, never chosen.
SELF_ASSIGNABLE_ROLES = {UserRole.BUYER, UserRole.SELLER}


@router.get("/users/me", name="get_me", response_model=UserOut)
async def get_me(user: CurrentUser) -> User:
    return user


@router.patch("/users/me", name="update_me", response_model=UserOut)
async def update_me(payload: UserUpdate, user: CurrentUser, session: SessionDep) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return user


@router.put(
    "/users/me/role",
    name="set_my_role",
    response_model=UserOut,
    responses={403: {"model": ErrorResponse}},
    summary="Switch between buying and selling",
)
async def set_my_role(payload: RoleUpdate, user: CurrentUser, session: SessionDep) -> User:
    if payload.role not in SELF_ASSIGNABLE_ROLES:
        raise forbidden("role_not_self_assignable")
    user.role = payload.role
    await session.commit()
    await session.refresh(user)
    return user


@router.get(
    "/users/me/export",
    name="export_my_data",
    summary="Download everything we store about you (PDPL)",
)
async def export_my_data(user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    return await users_service.export_personal_data(session, user)


@router.delete(
    "/users/me",
    name="delete_my_account",
    response_model=Ack,
    summary="Delete your account and personal data (PDPL)",
)
async def delete_my_account(user: CurrentUser, session: SessionDep) -> Ack:
    await users_service.delete_account(session, user)
    return Ack()


@router.get(
    "/users/{user_id}",
    name="get_user",
    response_model=PublicUserOut,
    responses={404: {"model": ErrorResponse}},
    summary="Public profile (never includes the phone number)",
)
async def get_user(user_id: uuid.UUID, session: SessionDep) -> User:
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise not_found("user_not_found")
    return user
