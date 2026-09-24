"""Reference data: Saudi cities and the vehicle taxonomy. Public and cacheable."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response
from sqlalchemy import select

from api.core.deps import SessionDep
from api.models.geo import City
from api.models.taxonomy import Make, Trim, VehicleModel
from api.schemas.geo import CityOut
from api.schemas.taxonomy import MakeOut, TrimOut, VehicleModelOut

router = APIRouter(tags=["reference"])

# Reference data changes rarely; let browsers and CDNs hold it for an hour.
CACHE_CONTROL = "public, max-age=3600"

MakeFilter = Query(description="Filter to one make")
ModelFilter = Query(description="Model to list trims for")


@router.get("/cities", name="list_cities", response_model=list[CityOut])
async def list_cities(session: SessionDep, response: Response) -> list[City]:
    response.headers["Cache-Control"] = CACHE_CONTROL
    rows = await session.execute(
        select(City).where(City.is_active).order_by(City.sort_order, City.name_en)
    )
    return list(rows.scalars())


@router.get("/makes", name="list_makes", response_model=list[MakeOut])
async def list_makes(session: SessionDep, response: Response) -> list[Make]:
    response.headers["Cache-Control"] = CACHE_CONTROL
    rows = await session.execute(
        select(Make).where(Make.is_active).order_by(Make.sort_order, Make.name_en)
    )
    return list(rows.scalars())


@router.get("/models", name="list_models", response_model=list[VehicleModelOut])
async def list_models(
    session: SessionDep,
    response: Response,
    make_id: Annotated[uuid.UUID | None, MakeFilter] = None,
) -> list[VehicleModel]:
    response.headers["Cache-Control"] = CACHE_CONTROL
    statement = select(VehicleModel).where(VehicleModel.is_active)
    if make_id is not None:
        statement = statement.where(VehicleModel.make_id == make_id)
    rows = await session.execute(statement.order_by(VehicleModel.sort_order, VehicleModel.name_en))
    return list(rows.scalars())


@router.get("/trims", name="list_trims", response_model=list[TrimOut])
async def list_trims(
    session: SessionDep,
    response: Response,
    model_id: Annotated[uuid.UUID, ModelFilter],
) -> list[Trim]:
    response.headers["Cache-Control"] = CACHE_CONTROL
    rows = await session.execute(
        select(Trim)
        .where(Trim.is_active, Trim.model_id == model_id)
        .order_by(Trim.sort_order, Trim.name_en)
    )
    return list(rows.scalars())
