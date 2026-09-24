"""Fixed-window rate limiting backed by Redis."""

from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_s: int


async def hit(redis: Redis, key: str, *, limit: int, window_s: int) -> RateLimitResult:
    """Count one attempt against `key`. The window starts at the first attempt."""
    pipeline = redis.pipeline()
    pipeline.incr(key)
    pipeline.ttl(key)
    count, ttl = await pipeline.execute()

    if ttl < 0:  # first hit in this window (or a key left without a TTL)
        await redis.expire(key, window_s)
        ttl = window_s

    if count > limit:
        return RateLimitResult(allowed=False, remaining=0, retry_after_s=max(ttl, 1))
    return RateLimitResult(allowed=True, remaining=limit - count, retry_after_s=0)


async def reset(redis: Redis, key: str) -> None:
    await redis.delete(key)
