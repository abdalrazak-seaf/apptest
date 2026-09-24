"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from api.core.config import get_settings
from api.core.errors import error_tracker
from api.core.logging import configure_logging
from api.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from api.routers import health, metrics


def _operation_id(route: APIRoute) -> str:
    # Stable, readable operation ids for the generated TypeScript client.
    return route.name


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
    app.add_exception_handler(Exception, _unhandled_exception)
    app.include_router(health.router)
    app.include_router(metrics.router)
    return app


app = create_app()
