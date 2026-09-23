from typing import Protocol


class StorageProvider(Protocol):
    async def ping(self) -> None:
        """Raise if the backing store is unreachable."""

    async def put_object(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get_object(self, key: str) -> bytes: ...

    async def presigned_get_url(self, key: str, expires_s: int = 900) -> str: ...
