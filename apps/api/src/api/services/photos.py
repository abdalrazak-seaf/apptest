"""Listing photo uploads.

Files are validated by their actual bytes, not the content type the client claims, then
stored through the StorageProvider interface (MinIO locally, S3 in real environments).
"""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.errors import conflict
from api.integrations.storage import StorageProvider
from api.models.listing import MAX_PHOTOS, Listing, ListingPhoto

logger = logging.getLogger(__name__)

MAX_PHOTO_BYTES = 8 * 1024 * 1024

# Magic bytes -> stored content type. The client's declared type is ignored.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


def sniff_image_type(data: bytes) -> str | None:
    """The image's real type, or None if these bytes are not a supported image."""
    for signature, content_type in _SIGNATURES:
        if data.startswith(signature):
            return content_type
    # WebP is "RIFF" + 4 size bytes + "WEBP".
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def add_photo(
    session: AsyncSession,
    storage: StorageProvider,
    *,
    listing: Listing,
    data: bytes,
    filename: str,
) -> ListingPhoto:
    if not data:
        raise conflict("photo_empty")
    if len(data) > MAX_PHOTO_BYTES:
        raise conflict("photo_too_large")

    content_type = sniff_image_type(data)
    if content_type is None:
        raise conflict("photo_unsupported_type")

    used = (
        await session.execute(
            select(func.count(ListingPhoto.id)).where(ListingPhoto.listing_id == listing.id)
        )
    ).scalar_one()
    if used >= MAX_PHOTOS:
        raise conflict("too_many_photos")

    next_position = (
        await session.execute(
            select(func.coalesce(func.max(ListingPhoto.position), -1) + 1).where(
                ListingPhoto.listing_id == listing.id
            )
        )
    ).scalar_one()

    extension = content_type.removeprefix("image/").replace("jpeg", "jpg")
    storage_key = f"listings/{listing.id}/{uuid.uuid4().hex}.{extension}"
    await storage.put_object(storage_key, data, content_type)

    photo = ListingPhoto(
        listing_id=listing.id,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=len(data),
        position=next_position,
        # Perceptual hashing for duplicate detection arrives with the fraud layer (Phase 5).
        perceptual_hash=None,
    )
    session.add(photo)
    logger.info(
        "listing_photo_uploaded",
        extra={
            "listing_id": str(listing.id),
            "size_bytes": len(data),
            "content_type": content_type,
            "original_filename": filename[:100],
        },
    )
    return photo


async def photo_urls(
    storage: StorageProvider, photos: list[ListingPhoto], *, expires_s: int = 3600
) -> dict[uuid.UUID, str]:
    """Signed, expiring URLs. Media is never served from a public bucket."""
    return {
        photo.id: await storage.presigned_get_url(photo.storage_key, expires_s) for photo in photos
    }
