"""Error tracking hook and the API's error contract.

Clients receive a machine-readable code (e.g. `{"code": "otp_invalid"}`) and translate it
themselves — error text is never sent in a single language from the server.
"""

import logging
from typing import Any, Protocol

from fastapi import HTTPException, status

logger = logging.getLogger("api.errors")


class ErrorTracker(Protocol):
    def capture_exception(self, exc: BaseException) -> None: ...


class LoggingErrorTracker:
    def capture_exception(self, exc: BaseException) -> None:
        logger.error("unhandled_exception", exc_info=exc)


error_tracker: ErrorTracker = LoggingErrorTracker()


class ApiError(HTTPException):
    """An error the client can act on, identified by a stable code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        *,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"code": code}
        if details:
            payload["details"] = details
        super().__init__(status_code=status_code, detail=payload, headers=headers)
        self.code = code


def not_found(code: str) -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, code)


def forbidden(code: str = "forbidden") -> ApiError:
    return ApiError(status.HTTP_403_FORBIDDEN, code)


def unauthorized(code: str = "not_authenticated") -> ApiError:
    return ApiError(status.HTTP_401_UNAUTHORIZED, code, headers={"WWW-Authenticate": "Bearer"})


def conflict(code: str) -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, code)


def too_many_requests(code: str, *, retry_after_s: int) -> ApiError:
    return ApiError(
        status.HTTP_429_TOO_MANY_REQUESTS,
        code,
        details={"retry_after_s": retry_after_s},
        headers={"Retry-After": str(retry_after_s)},
    )
