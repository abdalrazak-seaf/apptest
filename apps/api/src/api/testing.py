"""Pytest fixtures shared by the API's tests (registered from tests/conftest.py).

Tests run against a real PostgreSQL database because the schema uses PostGIS and other
Postgres-specific types. Each test runs inside a transaction that is rolled back afterwards,
so tests never see each other's rows. Redis is replaced by an in-process fake and SMS by the
mock provider, so no test touches the network.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

import pytest
from alembic import command
from alembic.config import Config
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api.core.config import Settings, get_settings
from api.core.db import get_session
from api.core.redis import get_redis
from api.core.security import create_access_token
from api.integrations.sms import MockSmsProvider, get_sms_provider
from api.main import create_app
from api.models.enums import ListingStatus, UserRole
from api.models.geo import City
from api.models.listing import Listing
from api.models.taxonomy import Make, Trim, VehicleModel
from api.models.user import User

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://thiqa:thiqa@localhost:5432/thiqa_test"
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test that touches the database as `integration`.

    `make test-unit` then runs only the tests that need no infrastructure, while
    `make test` (and CI) runs everything.
    """
    for item in items:
        if "connection" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.integration)


class UserFactory(Protocol):
    """Creates a user with a unique, valid Saudi mobile number."""

    async def __call__(
        self,
        *,
        role: UserRole = UserRole.BUYER,
        name: str | None = "مشتري",
        phone: str | None = None,
    ) -> User: ...


class AuthHeaders(Protocol):
    """Builds an Authorization header for a user, skipping the OTP round trip."""

    def __call__(self, user: User) -> dict[str, str]: ...


@pytest.fixture(scope="session")
def settings() -> Settings:
    get_settings.cache_clear()
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    return get_settings()


@pytest.fixture(scope="session")
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL)
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    config.attributes["database_url"] = TEST_DATABASE_URL
    await asyncio.to_thread(command.upgrade, config, "head")
    yield engine
    await engine.dispose()


@pytest.fixture
async def connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        yield connection
        await transaction.rollback()


@pytest.fixture
async def session(connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    # `create_savepoint` turns the application's commits into savepoint releases, so the
    # outer transaction above can still roll the whole test back.
    maker = async_sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    async with maker() as session:
        yield session


@pytest.fixture
def redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def sms() -> MockSmsProvider:
    return MockSmsProvider()


@pytest.fixture
def app(session: AsyncSession, redis: FakeAsyncRedis, sms: MockSmsProvider) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_sms_provider] = lambda: sms
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def city(session: AsyncSession) -> City:
    city = City(
        slug=f"riyadh-{uuid.uuid4().hex[:8]}",
        name_ar="الرياض",
        name_en="Riyadh",
        region_ar="منطقة الرياض",
        region_en="Riyadh Region",
        location="SRID=4326;POINT(46.6753 24.7136)",
        sort_order=1,
    )
    session.add(city)
    await session.commit()
    return city


@pytest.fixture
def make_user(session: AsyncSession) -> UserFactory:
    async def factory(
        *,
        role: UserRole = UserRole.BUYER,
        name: str | None = "مشتري",
        phone: str | None = None,
    ) -> User:
        user = User(phone=phone or f"+9665{uuid.uuid4().int % 10**8:08d}", role=role, name=name)
        session.add(user)
        await session.commit()
        return user

    return factory


@pytest.fixture
def auth_headers(settings: Settings) -> AuthHeaders:
    def headers(user: User) -> dict[str, str]:
        token = create_access_token(settings, user_id=user.id, role=user.role)
        return {"Authorization": f"Bearer {token}"}

    return headers


@pytest.fixture
async def make(session: AsyncSession) -> Make:
    """A make/model/trim tree with the Arabic aliases search relies on."""
    make = Make(
        slug=f"gmc-{uuid.uuid4().hex[:8]}",
        name_ar="جي إم سي",
        name_en="GMC",
        aliases=["جمس", "gmc"],
        sort_order=1,
    )
    session.add(make)
    await session.commit()
    return make


@pytest.fixture
async def vehicle_model(session: AsyncSession, make: Make) -> VehicleModel:
    model = VehicleModel(
        make_id=make.id,
        slug="yukon",
        name_ar="يوكن",
        name_en="Yukon",
        aliases=["يوكن", "yukon"],
        body_type="suv",
    )
    session.add(model)
    await session.commit()
    return model


@pytest.fixture
async def trim(session: AsyncSession, vehicle_model: VehicleModel) -> Trim:
    trim = Trim(
        model_id=vehicle_model.id,
        slug="denali",
        name_ar="دينالي",
        name_en="Denali",
        aliases=["دينالي", "denali"],
    )
    session.add(trim)
    await session.commit()
    return trim


class ListingFactory(Protocol):
    async def __call__(
        self,
        *,
        seller: User,
        status: ListingStatus = ListingStatus.ACTIVE,
        photos: int = 4,
        **fields: object,
    ) -> Listing: ...


@pytest.fixture
def make_listing(
    session: AsyncSession, city: City, make: Make, vehicle_model: VehicleModel
) -> ListingFactory:
    """Creates a listing directly in the database, bypassing the HTTP flow."""
    from api.models.listing import ListingPhoto
    from api.services.listings import build_search_text

    async def factory(
        *,
        seller: User,
        status: ListingStatus = ListingStatus.ACTIVE,
        photos: int = 4,
        **fields: object,
    ) -> Listing:
        defaults: dict[str, object] = {
            "make_id": make.id,
            "model_id": vehicle_model.id,
            "city_id": city.id,
            "year": 2019,
            "mileage_km": 85_000,
            "asking_price_sar": 90_000,
            "status": status,
        }
        defaults.update(fields)
        listing = Listing(seller_id=seller.id, **defaults)
        session.add(listing)
        await session.flush()
        for position in range(photos):
            session.add(
                ListingPhoto(
                    listing_id=listing.id,
                    storage_key=f"listings/{listing.id}/{position}.jpg",
                    content_type="image/jpeg",
                    size_bytes=1024,
                    position=position,
                )
            )
        listing.search_text = await build_search_text(session, listing)
        await session.commit()
        await session.refresh(listing, ["photos"])
        return listing

    return factory


def png_bytes() -> bytes:
    """The smallest valid PNG, for upload tests."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
