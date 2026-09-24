"""Object storage behind an interface (S3/MinIO in real envs, in-memory for tests/offline)."""

from functools import lru_cache

from api.core.config import get_settings
from api.integrations.storage.base import StorageProvider
from api.integrations.storage.memory import InMemoryStorage
from api.integrations.storage.s3 import S3Storage

__all__ = ["InMemoryStorage", "S3Storage", "StorageProvider", "get_storage"]


@lru_cache
def get_storage() -> StorageProvider:
    settings = get_settings()
    if settings.storage_provider == "memory":
        return InMemoryStorage()
    return S3Storage(settings)
