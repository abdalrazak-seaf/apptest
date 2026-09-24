"""Structured search: filters, sorting, and Arabic text matching."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.enums import ListingStatus, SellerType, Transmission
from api.models.geo import City
from api.models.taxonomy import Make
from api.models.user import User
from api.services.search import search_terms
from api.testing import ListingFactory, UserFactory


async def ids_from(client: AsyncClient, **params: str | int | bool) -> list[str]:
    response = await client.get("/listings", params=params)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


class TestVisibility:
    async def test_only_active_listings_are_searchable(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        active = await make_listing(seller=seller, status=ListingStatus.ACTIVE)
        for status in (
            ListingStatus.DRAFT,
            ListingStatus.PENDING_REVIEW,
            ListingStatus.HIDDEN,
            ListingStatus.REJECTED,
            ListingStatus.SOLD,
            ListingStatus.EXPIRED,
        ):
            await make_listing(seller=seller, status=status)

        assert await ids_from(client) == [str(active.id)]

    async def test_works_without_signing_in(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        await make_listing(seller=seller)
        response = await client.get("/listings")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_results_carry_a_cover_photo(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        await make_listing(seller=seller, photos=3)
        item = (await client.get("/listings")).json()["items"][0]
        assert item["cover_photo"]["position"] == 0
        assert item["cover_photo"]["url"]


class TestFilters:
    async def test_price_range(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        cheap = await make_listing(seller=seller, asking_price_sar=60_000)
        mid = await make_listing(seller=seller, asking_price_sar=90_000)
        await make_listing(seller=seller, asking_price_sar=150_000)

        found = await ids_from(client, price_min=60_000, price_max=90_000)
        assert sorted(found) == sorted([str(cheap.id), str(mid.id)])

    async def test_year_range_and_mileage(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        newer = await make_listing(seller=seller, year=2022, mileage_km=30_000)
        await make_listing(seller=seller, year=2015, mileage_km=200_000)

        assert await ids_from(client, year_min=2020) == [str(newer.id)]
        assert await ids_from(client, mileage_max=50_000) == [str(newer.id)]

    async def test_city_and_make(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        make_listing: ListingFactory,
        city: City,
        make: Make,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller)

        assert await ids_from(client, city_id=str(city.id)) == [str(listing.id)]
        assert await ids_from(client, make_id=str(make.id)) == [str(listing.id)]
        assert await ids_from(client, city_id=str(uuid.uuid4())) == []

    async def test_transmission_and_seller_type(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        automatic = await make_listing(seller=seller, transmission=Transmission.AUTOMATIC)
        await make_listing(seller=seller, transmission=Transmission.MANUAL)

        assert await ids_from(client, transmission="automatic") == [str(automatic.id)]
        assert len(await ids_from(client, seller_type=SellerType.PRIVATE)) == 2

    async def test_accident_free_filter(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        clean = await make_listing(seller=seller, accident_history_declared=False)
        await make_listing(seller=seller, accident_history_declared=True)

        assert await ids_from(client, accident_free=True) == [str(clean.id)]

    async def test_filters_combine_narrowly(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        match = await make_listing(seller=seller, year=2021, asking_price_sar=95_000)
        await make_listing(seller=seller, year=2021, asking_price_sar=200_000)
        await make_listing(seller=seller, year=2010, asking_price_sar=95_000)

        assert await ids_from(client, year_min=2020, price_max=100_000) == [str(match.id)]


class TestArabicText:
    async def test_finds_a_car_by_its_common_arabic_nickname(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller)

        # "جمس" is what buyers actually type for GMC.
        assert await ids_from(client, q="جمس") == [str(listing.id)]

    async def test_matches_the_english_name_too(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller)
        assert await ids_from(client, q="GMC Yukon") == [str(listing.id)]

    async def test_ignores_spelling_variants_and_arabic_digits(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, year=2019)

        for query in ("جمس ٢٠١٩", "جمس 2019", "يوكن"):
            assert await ids_from(client, q=query) == [str(listing.id)], query

    async def test_every_term_must_match(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        await make_listing(seller=seller, year=2019)

        assert await ids_from(client, q="جمس ٢٠١٩") != []
        # 2022 is not this car, so the whole query must fail.
        assert await ids_from(client, q="جمس ٢٠٢٢") == []

    async def test_searches_the_description(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, description_ar="ماشي قليل وفحص كامل")
        assert await ids_from(client, q="فحص") == [str(listing.id)]

    def test_query_terms_are_normalized(self) -> None:
        assert search_terms("أبي جمس ٢٠١٩  نظيف") == ["ابي", "جمس", "2019", "نظيف"]
        assert search_terms("   ") == []

    def test_absurdly_long_queries_are_truncated(self) -> None:
        assert len(search_terms(" ".join(["كلمة"] * 50))) == 8


class TestSorting:
    @pytest.mark.parametrize(
        ("sort", "expected_prices"),
        [
            ("price_asc", [60_000, 90_000, 150_000]),
            ("price_desc", [150_000, 90_000, 60_000]),
        ],
    )
    async def test_sorts_by_price(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        make_listing: ListingFactory,
        sort: str,
        expected_prices: list[int],
    ) -> None:
        seller: User = await make_user()
        for price in (90_000, 150_000, 60_000):
            await make_listing(seller=seller, asking_price_sar=price)

        response = await client.get("/listings", params={"sort": sort})
        assert [item["asking_price_sar"] for item in response.json()["items"]] == expected_prices

    async def test_sorts_by_mileage_and_year(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        await make_listing(seller=seller, mileage_km=120_000, year=2016)
        await make_listing(seller=seller, mileage_km=40_000, year=2023)

        by_mileage = await client.get("/listings", params={"sort": "mileage_asc"})
        assert [i["mileage_km"] for i in by_mileage.json()["items"]] == [40_000, 120_000]

        by_year = await client.get("/listings", params={"sort": "year_desc"})
        assert [i["year"] for i in by_year.json()["items"]] == [2023, 2016]

    async def test_rejects_an_unknown_sort(self, client: AsyncClient) -> None:
        assert (await client.get("/listings", params={"sort": "cheapest"})).status_code == 422


class TestPaging:
    async def test_pages_through_results(
        self, client: AsyncClient, make_user: UserFactory, make_listing: ListingFactory
    ) -> None:
        seller: User = await make_user()
        for price in range(50_000, 56_000, 1_000):
            await make_listing(seller=seller, asking_price_sar=price)

        first = await client.get("/listings", params={"limit": 2, "sort": "price_asc"})
        body = first.json()
        assert body["total"] == 6
        assert len(body["items"]) == 2
        assert body["items"][0]["asking_price_sar"] == 50_000

        second = await client.get(
            "/listings", params={"limit": 2, "offset": 2, "sort": "price_asc"}
        )
        assert second.json()["items"][0]["asking_price_sar"] == 52_000

    @pytest.mark.parametrize(("limit", "offset"), [(0, 0), (51, 0), (10, -1)])
    async def test_rejects_silly_paging(self, client: AsyncClient, limit: int, offset: int) -> None:
        response = await client.get("/listings", params={"limit": limit, "offset": offset})
        assert response.status_code == 422


class TestAnalytics:
    async def test_a_search_is_recorded(self, client: AsyncClient, session: AsyncSession) -> None:
        from sqlalchemy import select

        from api.models.event import Event, EventName

        await client.get("/listings", params={"q": "جمس"})
        events = (
            (await session.execute(select(Event).where(Event.name == EventName.LISTING_SEARCHED)))
            .scalars()
            .all()
        )
        assert len(events) == 1
        assert events[0].properties["has_query"] is True
