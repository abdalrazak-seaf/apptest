class InMemoryStorage:
    """Process-local storage for tests and fully offline runs."""

    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}

    async def ping(self) -> None:
        return None

    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self._objects[key] = (data, content_type)

    async def get_object(self, key: str) -> bytes:
        return self._objects[key][0]

    async def presigned_get_url(self, key: str, expires_s: int = 900) -> str:
        return f"memory://{key}?expires={expires_s}"
