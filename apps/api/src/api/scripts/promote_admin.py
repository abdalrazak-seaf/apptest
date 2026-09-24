"""Grant (or create) an admin account.

Usage: uv run python -m api.scripts.promote_admin 0501234567

There is deliberately no way to become an admin through the API, so the first administrator
is created here by someone with server access.
"""

import asyncio
import logging
import sys

from sqlalchemy import select

from api.core.config import get_settings
from api.core.db import get_engine, get_sessionmaker
from api.core.logging import configure_logging
from api.core.phone import mask_phone, normalize_saudi_phone
from api.models.enums import UserRole
from api.models.user import User

logger = logging.getLogger("api.promote_admin")


async def promote(raw_phone: str) -> None:
    phone = normalize_saudi_phone(raw_phone)
    if phone is None:
        raise SystemExit(f"Not a Saudi mobile number: {raw_phone}")

    async with get_sessionmaker()() as session:
        user = (await session.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
        created = user is None
        if user is None:
            user = User(phone=phone)
            session.add(user)
        user.role = UserRole.ADMIN
        user.is_active = True
        await session.commit()

    logger.info("admin_granted", extra={"phone": mask_phone(phone), "was_created": created})
    await get_engine().dispose()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m api.scripts.promote_admin <phone>")
    configure_logging(get_settings().log_level)
    asyncio.run(promote(sys.argv[1]))


if __name__ == "__main__":
    main()
