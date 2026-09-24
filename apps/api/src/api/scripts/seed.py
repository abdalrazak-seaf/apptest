"""Load reference data. Usage: uv run python -m api.scripts.seed

Idempotent: rows are matched by slug, so re-running updates names and aliases without
creating duplicates. Data comes only from the JSON files in `api/data/` — never scraped.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import get_settings
from api.core.db import get_engine, get_sessionmaker
from api.core.logging import configure_logging
from api.core.normalize import normalize_arabic
from api.models.geo import City
from api.models.taxonomy import Make, Trim, VehicleModel

logger = logging.getLogger("api.seed")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load(name: str) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads((DATA_DIR / name).read_text("utf-8"))
    return data


def build_aliases(entry: dict[str, Any]) -> list[str]:
    """Normalized search aliases: the Arabic and English names plus any spellings we know."""
    candidates = [entry["name_ar"], entry["name_en"], *entry.get("aliases", [])]
    seen: dict[str, None] = {}
    for candidate in candidates:
        normalized = normalize_arabic(candidate)
        if normalized:
            seen.setdefault(normalized, None)
    return list(seen)


async def seed_cities(session: AsyncSession) -> int:
    existing = {city.slug: city for city in (await session.execute(select(City))).scalars()}
    for entry in _load("cities.json"):
        city = existing.get(entry["slug"]) or City(slug=entry["slug"])
        city.name_ar = entry["name_ar"]
        city.name_en = entry["name_en"]
        city.region_ar = entry["region_ar"]
        city.region_en = entry["region_en"]
        city.location = f"SRID=4326;POINT({entry['lon']} {entry['lat']})"
        city.sort_order = entry["sort_order"]
        city.is_active = True
        session.add(city)
    await session.commit()
    return len(_load("cities.json"))


async def seed_taxonomy(session: AsyncSession) -> tuple[int, int, int]:
    makes = {m.slug: m for m in (await session.execute(select(Make))).scalars()}
    models = {
        (m.make_id, m.slug): m for m in (await session.execute(select(VehicleModel))).scalars()
    }
    trims = {(t.model_id, t.slug): t for t in (await session.execute(select(Trim))).scalars()}

    make_count = model_count = trim_count = 0
    for make_entry in _load("makes.json"):
        make = makes.get(make_entry["slug"]) or Make(slug=make_entry["slug"])
        make.name_ar = make_entry["name_ar"]
        make.name_en = make_entry["name_en"]
        make.aliases = build_aliases(make_entry)
        make.sort_order = make_entry["sort_order"]
        make.is_active = True
        session.add(make)
        await session.flush()
        make_count += 1

        for order, model_entry in enumerate(make_entry["models"], start=1):
            model = models.get((make.id, model_entry["slug"])) or VehicleModel(
                make_id=make.id, slug=model_entry["slug"]
            )
            model.name_ar = model_entry["name_ar"]
            model.name_en = model_entry["name_en"]
            model.aliases = build_aliases(model_entry)
            model.body_type = model_entry.get("body_type")
            model.sort_order = order
            model.is_active = True
            session.add(model)
            await session.flush()
            model_count += 1

            for trim_order, trim_entry in enumerate(model_entry.get("trims", []), start=1):
                trim = trims.get((model.id, trim_entry["slug"])) or Trim(
                    model_id=model.id, slug=trim_entry["slug"]
                )
                trim.name_ar = trim_entry["name_ar"]
                trim.name_en = trim_entry["name_en"]
                trim.aliases = build_aliases(trim_entry)
                trim.sort_order = trim_order
                trim.is_active = True
                session.add(trim)
                trim_count += 1

    await session.commit()
    return make_count, model_count, trim_count


async def run() -> None:
    async with get_sessionmaker()() as session:
        cities = await seed_cities(session)
        makes, models, trims = await seed_taxonomy(session)
    logger.info(
        "seed_complete",
        extra={"cities": cities, "makes": makes, "models": models, "trims": trims},
    )
    await get_engine().dispose()


def main() -> None:
    configure_logging(get_settings().log_level)
    asyncio.run(run())


if __name__ == "__main__":
    main()
