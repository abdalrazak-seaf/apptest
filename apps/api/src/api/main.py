"""FastAPI application factory."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException

from api.core.config import get_settings
from api.core.errors import error_tracker
from api.core.logging import configure_logging
from api.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from api.routers import auth, health, listings, metrics, reference, showrooms, users

# Shapes Starlette's own errors (unknown route, wrong method) like the rest of the API.
_FALLBACK_CODES = {404: "not_found", 405: "method_not_allowed"}


def _operation_id(route: APIRoute) -> str:
    # Stable, readable operation ids for the generated TypeScript client.
    return route.name


async def _http_exception(request: Request, exc: Exception) -> JSONResponse:
    """Render every error as {"code": ...}, never as a single-language message."""
    if not isinstance(exc, HTTPException):  # pragma: no cover - registered for HTTPException
        raise exc
    detail: Any = exc.detail
    body = (
        detail
        if isinstance(detail, dict) and "code" in detail
        else {"code": _FALLBACK_CODES.get(exc.status_code, "http_error")}
    )
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


async def _validation_exception(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # pragma: no cover
        raise exc
    fields = sorted({str(error["loc"][-1]) for error in exc.errors() if error.get("loc")})
    return JSONResponse(
        status_code=422, content={"code": "validation_error", "details": {"fields": fields}}
    )


async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    error_tracker.capture_exception(exc)
    return JSONResponse(status_code=500, content={"code": "internal_error"})


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=f"{settings.app_name} API",
        version=settings.app_version,
        generate_unique_id_function=_operation_id,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_exception_handler(HTTPException, _http_exception)
    app.add_exception_handler(RequestValidationError, _validation_exception)
    app.add_exception_handler(Exception, _unhandled_exception)

    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(listings.router)
    app.include_router(reference.router)
    app.include_router(showrooms.router)
    return app


app = create_app()
