"""Async Redis connection helper."""

from __future__ import annotations

from typing import Any

from redis.asyncio import Redis

from app.config.settings import Settings, get_settings

_client: Redis | None = None


async def get_redis(
    settings: Settings | None = None,
) -> Redis:
    """Return shared async Redis client."""
    global _client
    if _client is None:
        cfg = settings or get_settings()
        # Redis 5.x has no HELLO/RESP3; force protocol 2.
        _client = Redis.from_url(
            cfg.redis_url,
            decode_responses=True,
            protocol=2,
        )
    return _client


async def close_redis() -> None:
    """Close shared Redis client if open."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def redis_call(
    method: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Call a Redis method by name on shared client."""
    client = await get_redis()
    func = getattr(client, method)
    return await func(*args, **kwargs)
