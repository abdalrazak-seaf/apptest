"""ARQ worker entrypoint: `arq worker.main.WorkerSettings`."""

import logging
import time
from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings

from api.core.config import get_settings
from api.core.logging import configure_logging

logger = logging.getLogger("worker")

HEARTBEAT_KEY = "worker:heartbeat"
HEARTBEAT_TTL_S = 180


async def heartbeat(ctx: dict[str, Any]) -> float:
    """Record that the worker is alive. Ops can alert when the key expires."""
    now = time.time()
    await ctx["redis"].set(HEARTBEAT_KEY, str(now), ex=HEARTBEAT_TTL_S)
    return now


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging(get_settings().log_level)
    logger.info("worker_started")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker_stopped")


class WorkerSettings:
    functions: ClassVar[list[Any]] = [heartbeat]
    cron_jobs: ClassVar[list[Any]] = [cron(heartbeat, second=0, run_at_startup=True)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 10
    job_timeout = 300
