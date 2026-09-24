"""SQLAlchemy models. Import every model module here so Alembic sees it."""

from api.core.db import Base
from api.models.geo import City
from api.models.showroom import Showroom, ShowroomStaff
from api.models.taxonomy import Make, Trim, VehicleModel
from api.models.user import OtpRequest, RefreshToken, User

__all__ = [
    "Base",
    "City",
    "Make",
    "OtpRequest",
    "RefreshToken",
    "Showroom",
    "ShowroomStaff",
    "Trim",
    "User",
    "VehicleModel",
]
