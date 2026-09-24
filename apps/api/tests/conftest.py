import os

# Unit tests run fully offline: in-memory storage, no real network calls.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("STORAGE_PROVIDER", "memory")

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.main import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
