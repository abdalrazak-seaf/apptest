import asyncio

from fastapi import FastAPI
from httpx import AsyncClient

from api.routers.health import Check, get_readiness_checks


async def _ok() -> None:
    return None


async def _boom() -> None:
    raise ConnectionError("db-host:5432 refused")


async def _slow() -> None:
    await asyncio.sleep(10)


def _override(app: FastAPI, checks: dict[str, Check]) -> None:
    app.dependency_overrides[get_readiness_checks] = lambda: checks


async def test_health_is_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "api"
    assert body["environment"] == "test"


async def test_request_id_is_generated(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert len(response.headers["X-Request-ID"]) == 32


async def test_request_id_is_propagated(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


async def test_oversized_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "x" * 200})
    assert response.headers["X-Request-ID"] != "x" * 200


async def test_readiness_ok_when_all_checks_pass(app: FastAPI, client: AsyncClient) -> None:
    _override(app, {"database": _ok, "redis": _ok, "storage": _ok})
    response = await client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["checks"]) == {"database", "redis", "storage"}


async def test_readiness_503_and_hides_error_details(app: FastAPI, client: AsyncClient) -> None:
    _override(app, {"database": _boom, "redis": _ok})
    response = await client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"]["database"] == {
        "ok": False,
        "latency_ms": body["checks"]["database"]["latency_ms"],
        "error": "ConnectionError",
    }
    assert "db-host" not in response.text
    assert body["checks"]["redis"]["ok"] is True


async def test_readiness_times_out_slow_checks(
    app: FastAPI, client: AsyncClient, monkeypatch: object
) -> None:
    from api.core.config import get_settings

    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(
        update={"health_check_timeout_s": 0.05}
    )
    _override(app, {"redis": _slow})
    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["redis"]["error"] == "TimeoutError"


async def test_metrics_exposes_request_counters(client: AsyncClient) -> None:
    await client.get("/health")
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert 'http_requests_total{method="GET",route="/health"' in response.text


async def test_unhandled_errors_return_generic_500(app: FastAPI) -> None:
    from httpx import ASGITransport

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret detail")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/boom")
    assert response.status_code == 500
    assert response.json() == {"code": "internal_error"}
    assert "secret" not in response.text


async def test_unknown_routes_use_the_same_error_shape(client: AsyncClient) -> None:
    response = await client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"code": "not_found"}


async def test_wrong_method_uses_the_same_error_shape(client: AsyncClient) -> None:
    response = await client.post("/health")
    assert response.status_code == 405
    assert response.json() == {"code": "method_not_allowed"}
