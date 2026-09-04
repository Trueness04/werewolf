"""Dynamic import registry for AI agent classes."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from AI.base_agent import BaseAgent
from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import AI_AGENTS
from app.managers.json_loader import load_json


def ai_enabled() -> bool:
    """Master AI players switch (ai_agents.json 'enabled')."""
    return bool(load_json(AI_AGENTS).get("enabled", True))


async def ai_runtime_enabled() -> bool:
    """Runtime AI switch: Redis key first, json fallback.

    The Redis value ("1"/"0") is the live source of truth
    set by the sudo /ai command; when the key is missing
    (or Redis is unreachable) fall back to ai_agents.json
    'enabled'.
    """
    try:
        keys = RedisKeySpace()
        redis = await get_redis()
        raw = await redis.get(keys.ai_runtime_enabled())
    except Exception:
        # Redis unavailable: json config stays authoritative.
        return ai_enabled()
    if raw is None:
        return ai_enabled()
    return str(raw).strip().lower() in {"1", "true", "on"}


async def set_ai_runtime_enabled(enabled: bool) -> None:
    """Persist runtime AI switch in Redis (no TTL)."""
    keys = RedisKeySpace()
    redis = await get_redis()
    await redis.set(
        keys.ai_runtime_enabled(),
        "1" if enabled else "0",
    )


class AgentRegistry:
    """Create agents from config class path."""

    def __init__(self) -> None:
        self._cfg = load_json(AI_AGENTS)

    @property
    def config(self) -> dict[str, Any]:
        """Return ai_agents.json document."""
        return self._cfg

    def create(
        self,
        user_id: int,
        name: str,
        class_path: str | None = None,
    ) -> BaseAgent:
        """Instantiate configured agent class."""
        path = class_path or str(
            self._cfg["default_agent"]
        )
        module_name, _, cls_name = path.rpartition(".")
        module = import_module(module_name)
        cls = getattr(module, cls_name)
        agent = cls(user_id, name)
        if not isinstance(agent, BaseAgent):
            raise TypeError(path)
        return agent

    def make_user_id(self, index: int) -> int:
        """Stable negative id for AI seat index."""
        base = int(self._cfg["id_base"])
        return base - (index + 1)

    def make_name(self, index: int) -> str:
        """Display name for AI seat index."""
        prefix = str(self._cfg["name_prefix"])
        return f"{prefix}{index + 1}"

    def is_ai_id(self, user_id: int) -> bool:
        """True when user_id is in AI id space."""
        base = int(self._cfg["id_base"])
        return user_id <= base - 1
