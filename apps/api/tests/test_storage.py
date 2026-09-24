from api.integrations.storage import InMemoryStorage


async def test_in_memory_storage_roundtrip() -> None:
    storage = InMemoryStorage()
    await storage.ping()
    await storage.put_object("a/b.jpg", b"data", "image/jpeg")
    assert await storage.get_object("a/b.jpg") == b"data"
    assert (await storage.presigned_get_url("a/b.jpg", 60)).startswith("memory://a/b.jpg")
