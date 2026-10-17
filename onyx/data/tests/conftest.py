"""Shared pytest fixtures for the onyx test suite."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeRedis:
    """In-memory redis stub for manager unit tests."""

    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.kv: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}

    async def hget(
        self,
        key: str,
        field: str,
    ) -> str | None:
        return self.hashes.get(key, {}).get(field)

    async def hset(
        self,
        key: str,
        field: str | None = None,
        value: str | None = None,
        mapping: dict | None = None,
    ) -> int:
        bucket = self.hashes.setdefault(key, {})
        n = 0
        if mapping:
            for k, v in mapping.items():
                bucket[str(k)] = str(v)
                n += 1
        if field is not None and value is not None:
            bucket[str(field)] = str(value)
            n += 1
        return n

    async def hdel(self, key: str, *fields: str) -> int:
        bucket = self.hashes.get(key, {})
        n = 0
        for f in fields:
            if f in bucket:
                del bucket[f]
                n += 1
        return n

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    async def get(self, key: str) -> str | None:
        return self.kv.get(key)

    async def set(self, key: str, value: str) -> bool:
        self.kv[key] = str(value)
        return True

    async def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self.kv:
                del self.kv[k]
                n += 1
            if k in self.hashes:
                del self.hashes[k]
                n += 1
            if k in self.sets:
                del self.sets[k]
                n += 1
        return n

    async def sadd(self, key: str, *members: str) -> int:
        s = self.sets.setdefault(key, set())
        before = len(s)
        s.update(str(m) for m in members)
        return len(s) - before

    async def sismember(self, key: str, member: str) -> bool:
        return str(member) in self.sets.get(key, set())

    async def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    async def srem(self, key: str, *members: str) -> int:
        s = self.sets.get(key, set())
        n = 0
        for m in members:
            if str(m) in s:
                s.discard(str(m))
                n += 1
        return n

    async def scard(self, key: str) -> int:
        return len(self.sets.get(key, set()))

    async def expire(self, key: str, _sec: int) -> bool:
        return key in self.kv or key in self.hashes or key in self.sets
