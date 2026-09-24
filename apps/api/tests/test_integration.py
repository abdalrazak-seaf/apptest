"""Tests against real Postgres/Redis/MinIO. Run `make infra-up` first."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from api.core.config import get_settings
from api.main import create_app

pytestmark = pytest.mark.integration

ALEMBIC_INI = Path(__file__).parents[1] / "alembic.ini"


async def _extensions() -> set[str]:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT extname FROM pg_extension"))
        names = {r[0] for r in rows}
    await engine.dispose()
    return names


def _alembic(cmd: str, rev: str) -> None:
    cfg = Config(str(ALEMBIC_INI))
    getattr(command, cmd)(cfg, rev)


async def test_migrations_are_reversible() -> None:
    import asyncio

    await asyncio.to_thread(_alembic, "upgrade", "head")
    assert {"postgis", "vector", "pg_trgm"} <= await _extensions()
    await asyncio.to_thread(_alembic, "downgrade", "base")
    assert "vector" not in await _extensions()
    await asyncio.to_thread(_alembic, "upgrade", "head")


async def test_readiness_against_real_services(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_PROVIDER", os.environ.get("INTEGRATION_STORAGE_PROVIDER", "s3"))
    from api.integrations.storage import get_storage

    get_settings.cache_clear()
    get_storage.cache_clear()
    try:
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            response = await c.get("/health/ready")
        assert response.status_code == 200, response.text
    finally:
        get_settings.cache_clear()
        get_storage.cache_clear()
