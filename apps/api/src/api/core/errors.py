"""Error tracking hook. The provider is an open decision; the default only logs."""

import logging
from typing import Protocol

logger = logging.getLogger("api.errors")


class ErrorTracker(Protocol):
    def capture_exception(self, exc: BaseException) -> None: ...


class LoggingErrorTracker:
    def capture_exception(self, exc: BaseException) -> None:
        logger.error("unhandled_exception", exc_info=exc)


error_tracker: ErrorTracker = LoggingErrorTracker()
