"""SQLAlchemy models. Import every model module here so Alembic sees it."""

from api.core.db import Base

__all__ = ["Base"]
