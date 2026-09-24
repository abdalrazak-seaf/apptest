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


class ListingStatus(StrEnum):
    """Every non-active status carries a reason the seller can read (see StatusReasonCode)."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    HIDDEN = "hidden"
    REJECTED = "rejected"
    SOLD = "sold"
    EXPIRED = "expired"


class StatusReasonCode(StrEnum):
    """Why a listing is not active. Clients translate these; we never send prose."""

    # Seller-driven
    SELLER_DRAFT = "seller_draft"
    SELLER_HID = "seller_hid"
    SELLER_SOLD = "seller_sold"
    SELLER_REPUBLISHED = "seller_republished"
    # Review-driven
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    MISSING_PHOTOS = "missing_photos"
    INCOMPLETE_DETAILS = "incomplete_details"
    SUSPECTED_DUPLICATE = "suspected_duplicate"
    PRICE_ANOMALY = "price_anomaly"
    PROHIBITED_CONTENT = "prohibited_content"
    CONTACT_IN_DESCRIPTION = "contact_in_description"
    SUSPECTED_FRAUD = "suspected_fraud"
    # Time-driven
    EXPIRED_UNSOLD = "expired_unsold"


class Transmission(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class FuelType(StrEnum):
    PETROL = "petrol"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    ELECTRIC = "electric"


class RegionalSpec(StrEnum):
    """Where the car was originally specified for; it affects price in the Saudi market."""

    SAUDI = "saudi"
    GCC = "gcc"
    AMERICAN = "american"
    OTHER = "other"


class SellerType(StrEnum):
    PRIVATE = "private"
    SHOWROOM = "showroom"
