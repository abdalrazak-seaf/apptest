"""Liveness and readiness probes."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text

from api.core.config import Settings, get_settings
from api.core.db import get_engine
from api.core.redis import get_redis
from api.integrations.storage import get_storage
from api.schemas.health import DependencyCheck, HealthResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["health"])

Check = Callable[[], Awaitable[object]]


async def _check_database() -> None:
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


async def _check_redis() -> None:
    await get_redis().ping()


async def _check_storage() -> None:
    await get_storage().ping()


def get_readiness_checks() -> dict[str, Check]:
    return {"database": _check_database, "redis": _check_redis, "storage": _check_storage}


async def _run_check(check: Check, timeout_s: float) -> DependencyCheck:
    start = time.perf_counter()
    try:
        await asyncio.wait_for(check(), timeout=timeout_s)
    except Exception as exc:  # any failure means "not ready"
        return DependencyCheck(
            ok=False,
            latency_ms=round((time.perf_counter() - start) * 1000, 1),
            error=type(exc).__name__,
        )
    return DependencyCheck(ok=True, latency_ms=round((time.perf_counter() - start) * 1000, 1))


@router.get("", response_model=HealthResponse, name="get_health")
async def get_health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Liveness: the process is up. Does not touch dependencies."""
    return HealthResponse(
        status="ok",
        service="api",
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    name="get_readiness",
    responses={503: {"model": ReadinessResponse}},
)
async def get_readiness(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    checks: Annotated[dict[str, Check], Depends(get_readiness_checks)],
) -> ReadinessResponse:
    """Readiness: database, Redis and object storage are reachable."""
    names = list(checks)
    results = await asyncio.gather(
        *(_run_check(checks[n], settings.health_check_timeout_s) for n in names)
    )
    by_name = dict(zip(names, results, strict=True))
    ready = all(r.ok for r in results)
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(status="ok" if ready else "unavailable", checks=by_name)
