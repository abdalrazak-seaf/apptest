"""Domain enumerations.

Stored as VARCHAR with a CHECK constraint (`native_enum=False`) rather than a Postgres
ENUM type: adding a value is then an ordinary, reversible migration.
"""

from enum import StrEnum


class Language(StrEnum):
    AR = "ar"
    EN = "en"


class UserRole(StrEnum):
    BUYER = "buyer"
    SELLER = "seller"
    SHOWROOM_STAFF = "showroom_staff"
    ADMIN = "admin"


class ShowroomStaffRole(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    AGENT = "agent"


class SubscriptionTier(StrEnum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"


class BodyType(StrEnum):
    SEDAN = "sedan"
    SUV = "suv"
    PICKUP = "pickup"
    HATCHBACK = "hatchback"
    COUPE = "coupe"
    VAN = "van"
    OTHER = "other"
