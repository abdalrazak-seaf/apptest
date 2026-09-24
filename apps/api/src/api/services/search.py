"""Structured listing search.

Phase 5 adds conversational search on top; this layer stays purely structured so the
filters always work without AI, exactly as the brief requires.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload

from api.core.normalize import normalize_arabic
from api.models.enums import (
    BodyType,
    FuelType,
    ListingStatus,
    RegionalSpec,
    SellerType,
    Transmission,
)
from api.models.listing import Listing

# Longer queries are almost certainly a paste; ignore the tail rather than scanning for it.
MAX_QUERY_TERMS = 8


class SortOrder(StrEnum):
    NEWEST = "newest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    MILEAGE_ASC = "mileage_asc"
    YEAR_DESC = "year_desc"


@dataclass(frozen=True)
class ListingFilters:
    query: str | None = None
    make_id: Any | None = None
    model_id: Any | None = None
    trim_id: Any | None = None
    city_id: Any | None = None
    year_min: int | None = None
    year_max: int | None = None
    price_min: int | None = None
    price_max: int | None = None
    mileage_max: int | None = None
    body_type: BodyType | None = None
    transmission: Transmission | None = None
    fuel_type: FuelType | None = None
    regional_spec: RegionalSpec | None = None
    seller_type: SellerType | None = None
    # True keeps only listings whose seller declared no accident history.
    accident_free: bool | None = None
    sort: SortOrder = SortOrder.NEWEST


_SORTS = {
    SortOrder.NEWEST: (Listing.published_at.desc().nullslast(), Listing.created_at.desc()),
    SortOrder.PRICE_ASC: (Listing.asking_price_sar.asc(),),
    SortOrder.PRICE_DESC: (Listing.asking_price_sar.desc(),),
    SortOrder.MILEAGE_ASC: (Listing.mileage_km.asc(),),
    SortOrder.YEAR_DESC: (Listing.year.desc(),),
}


def search_terms(query: str) -> list[str]:
    """Normalized words from a buyer's query ('جمس ٢٠١٩' -> ['جمس', '2019'])."""
    return [term for term in normalize_arabic(query).split() if term][:MAX_QUERY_TERMS]


def apply_filters(statement: Select[Any], filters: ListingFilters) -> Select[Any]:
    """Narrow a listing query. Only active listings are searchable."""
    statement = statement.where(Listing.status == ListingStatus.ACTIVE)

    simple = {
        Listing.make_id: filters.make_id,
        Listing.model_id: filters.model_id,
        Listing.trim_id: filters.trim_id,
        Listing.city_id: filters.city_id,
        Listing.body_type: filters.body_type,
        Listing.transmission: filters.transmission,
        Listing.fuel_type: filters.fuel_type,
        Listing.regional_spec: filters.regional_spec,
        Listing.seller_type: filters.seller_type,
    }
    for column, value in simple.items():
        if value is not None:
            statement = statement.where(column == value)

    # Built lazily: comparing a column with None raises rather than matching everything.
    ranges: list[tuple[Any, str, int | None]] = [
        (Listing.year, "ge", filters.year_min),
        (Listing.year, "le", filters.year_max),
        (Listing.asking_price_sar, "ge", filters.price_min),
        (Listing.asking_price_sar, "le", filters.price_max),
        (Listing.mileage_km, "le", filters.mileage_max),
    ]
    for column, operator, value in ranges:
        if value is not None:
            statement = statement.where(column >= value if operator == "ge" else column <= value)

    if filters.accident_free:
        statement = statement.where(Listing.accident_history_declared.is_(False))

    if filters.query:
        # Every term must appear, so "جمس ٢٠١٩" narrows instead of widening.
        for term in search_terms(filters.query):
            statement = statement.where(Listing.search_text.contains(term))

    return statement


def build_search_query(filters: ListingFilters, *, limit: int, offset: int) -> Select[Any]:
    statement = apply_filters(select(Listing), filters).options(selectinload(Listing.photos))
    return statement.order_by(*_SORTS[filters.sort]).limit(limit).offset(offset)


def build_count_query(filters: ListingFilters) -> Select[Any]:
    return apply_filters(select(func.count(Listing.id)), filters)
