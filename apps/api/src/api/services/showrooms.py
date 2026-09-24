"""Showroom membership rules."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.enums import ShowroomStaffRole, UserRole
from api.models.showroom import ShowroomStaff
from api.models.user import User

# Roles allowed to change a showroom's details or its staff list.
MANAGING_ROLES = {ShowroomStaffRole.OWNER, ShowroomStaffRole.MANAGER}


async def get_membership(
    session: AsyncSession, *, showroom_id: uuid.UUID, user_id: uuid.UUID
) -> ShowroomStaff | None:
    return (
        await session.execute(
            select(ShowroomStaff).where(
                ShowroomStaff.showroom_id == showroom_id,
                ShowroomStaff.user_id == user_id,
            )
        )
    ).scalar_one_or_none()


async def may_manage(session: AsyncSession, *, showroom_id: uuid.UUID, user: User) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    membership = await get_membership(session, showroom_id=showroom_id, user_id=user.id)
    return membership is not None and membership.role in MANAGING_ROLES


async def is_staff(session: AsyncSession, *, showroom_id: uuid.UUID, user: User) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    return await get_membership(session, showroom_id=showroom_id, user_id=user.id) is not None
