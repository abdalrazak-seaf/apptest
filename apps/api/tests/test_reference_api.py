"""Cities and the vehicle taxonomy, including the Arabic aliases used by search."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.normalize import normalize_arabic
from api.models.geo import City
from api.models.taxonomy import Make, Trim, VehicleModel
from api.scripts.seed import build_aliases


async def seed_gmc(session: AsyncSession) -> tuple[Make, VehicleModel, Trim]:
    make = Make(
        slug=f"gmc-{uuid.uuid4().hex[:6]}",
        name_ar="جي إم سي",
        name_en="GMC",
        aliases=["جمس", "gmc"],
        sort_order=1,
    )
    session.add(make)
    await session.flush()
    model = VehicleModel(
        make_id=make.id, slug="yukon", name_ar="يوكن", name_en="Yukon", body_type="suv"
    )
    session.add(model)
    await session.flush()
    trim = Trim(model_id=model.id, slug="denali", name_ar="دينالي", name_en="Denali")
    session.add(trim)
    await session.commit()
    return make, model, trim


class TestCities:
    async def test_lists_active_cities_without_signing_in(
        self, client: AsyncClient, city: City
    ) -> None:
        response = await client.get("/cities")
        assert response.status_code == 200
        slugs = [c["slug"] for c in response.json()]
        assert city.slug in slugs

    async def test_hides_inactive_cities(
        self, client: AsyncClient, city: City, session: AsyncSession
    ) -> None:
        city.is_active = False
        await session.commit()
        slugs = [c["slug"] for c in (await client.get("/cities")).json()]
        assert city.slug not in slugs

    async def test_returns_both_languages(self, client: AsyncClient, city: City) -> None:
        entry = next(c for c in (await client.get("/cities")).json() if c["slug"] == city.slug)
        assert entry["name_ar"] == "الرياض"
        assert entry["name_en"] == "Riyadh"
        assert entry["region_ar"]

    async def test_is_cacheable(self, client: AsyncClient) -> None:
        response = await client.get("/cities")
        assert "max-age" in response.headers["Cache-Control"]


class TestTaxonomy:
    async def test_lists_makes(self, client: AsyncClient, session: AsyncSession) -> None:
        make, _, _ = await seed_gmc(session)
        slugs = [m["slug"] for m in (await client.get("/makes")).json()]
        assert make.slug in slugs

    async def test_models_can_be_filtered_by_make(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        make, model, _ = await seed_gmc(session)
        response = await client.get("/models", params={"make_id": str(make.id)})
        assert response.status_code == 200
        body = response.json()
        assert [m["slug"] for m in body] == [model.slug]
        assert body[0]["body_type"] == "suv"

    async def test_models_for_an_unknown_make_are_empty(self, client: AsyncClient) -> None:
        response = await client.get("/models", params={"make_id": str(uuid.uuid4())})
        assert response.status_code == 200
        assert response.json() == []

    async def test_lists_trims_of_a_model(self, client: AsyncClient, session: AsyncSession) -> None:
        _, model, trim = await seed_gmc(session)
        response = await client.get("/trims", params={"model_id": str(model.id)})
        assert [t["slug"] for t in response.json()] == [trim.slug]

    async def test_trims_require_a_model(self, client: AsyncClient) -> None:
        assert (await client.get("/trims")).status_code == 422


class TestAliases:
    def test_aliases_are_normalized_for_arabic_search(self) -> None:
        aliases = build_aliases(
            {"name_ar": "جي إم سي", "name_en": "GMC", "aliases": ["جمس", "جيمس"]}
        )
        assert normalize_arabic("جمس") in aliases
        assert "gmc" in aliases, "English names are lowercased for matching"
        assert all(alias == normalize_arabic(alias) for alias in aliases)

    def test_aliases_are_deduplicated(self) -> None:
        aliases = build_aliases(
            {"name_ar": "كامري", "name_en": "Camry", "aliases": ["كامري", "كمري"]}
        )
        assert len(aliases) == len(set(aliases))

    def test_spelling_variants_collapse_to_one_alias(self) -> None:
        # أ/ا and ة/ه differences must not create separate aliases.
        aliases = build_aliases({"name_ar": "أكسنت", "name_en": "Accent", "aliases": ["اكسنت"]})
        assert aliases.count(normalize_arabic("اكسنت")) == 1
