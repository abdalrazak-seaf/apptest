"""Profile updates, PDPL data export and account deletion."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.showroom import ShowroomStaff
from api.models.user import RefreshToken, User
from api.services.auth import revoke_all_for_user


async def export_personal_data(session: AsyncSession, user: User) -> dict[str, Any]:
    """Everything we hold about this user, for a PDPL data-access request."""
    sessions = (
        (await session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id)))
        .scalars()
        .all()
    )
    memberships = (
        (await session.execute(select(ShowroomStaff).where(ShowroomStaff.user_id == user.id)))
        .scalars()
        .all()
    )

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "profile": {
            "id": str(user.id),
            "phone": user.phone,
            "name": user.name,
            "preferred_language": user.preferred_language,
            "role": user.role,
            "city_id": str(user.city_id) if user.city_id else None,
            "identity_verified": user.identity_verified,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        },
        "showroom_memberships": [
            {"showroom_id": str(m.showroom_id), "role": m.role} for m in memberships
        ],
        # Tokens themselves are stored hashed and are never exported.
        "login_sessions": [
            {
                "created_at": s.created_at.isoformat(),
                "user_agent": s.user_agent,
                "revoked": s.revoked_at is not None,
            }
            for s in sessions
        ],
    }


def _tombstone_phone() -> str:
    """A unique, non-dialable placeholder so the real number is released and unlinkable."""
    return f"+000{uuid.uuid4().hex[:16]}"


async def delete_account(session: AsyncSession, user: User) -> None:
    """Erase personal details, disable login, and keep rows other people's data depends on."""
    await revoke_all_for_user(session, user.id)
    user.phone = _tombstone_phone()
    user.name = None
    user.city_id = None
    user.identity_verified = False
    user.identity_provider = None
    user.is_active = False
    user.deleted_at = datetime.now(UTC)
    await session.commit()
