from typing import Any

from worker.main import HEARTBEAT_KEY, HEARTBEAT_TTL_S, WorkerSettings, heartbeat


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, tuple[str, int | None]] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = (value, ex)


async def test_heartbeat_writes_key_with_ttl() -> None:
    redis = FakeRedis()
    ctx: dict[str, Any] = {"redis": redis}
    ts = await heartbeat(ctx)
    value, ttl = redis.store[HEARTBEAT_KEY]
    assert float(value) == ts
    assert ttl == HEARTBEAT_TTL_S


def test_worker_registers_heartbeat() -> None:
    assert heartbeat in WorkerSettings.functions
