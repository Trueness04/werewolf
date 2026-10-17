"""Role setup hooks (assign deferred)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.game_event import log_game_event


class RoleBalanceError(Exception):
    """Raised when role balance cannot complete."""


AssignRolesFn = Callable[[int], Awaitable[None]]


class RoleSetupManager:
    """Unlock roles + injectable assign hook."""

    def __init__(
        self,
        keys: RedisKeySpace | None = None,
        assign_fn: AssignRolesFn | None = None,
    ) -> None:
        self._keys = keys or RedisKeySpace()
        self._assign_fn = assign_fn

    def set_assign_hook(
        self,
        assign_fn: AssignRolesFn,
    ) -> None:
        """Register role assignment callable."""
        self._assign_fn = assign_fn

    async def unlock_all_roles(
        self,
        chat_id: int,
    ) -> None:
        """Mark SetUpRoles in Redis for the lobby."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("setup_roles")
        await redis.hset(key, field, "1")
        log_game_event(
            "roles_unlocked",
            chat_id=chat_id,
        )

    async def is_setup_done(
        self,
        chat_id: int,
    ) -> bool:
        """Return True if SetUpRoles already set."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("setup_roles")
        value = await redis.hget(key, field)
        return bool(value)

    async def assign_roles(self, chat_id: int) -> None:
        """Call inject hook or no-op success."""
        if self._assign_fn is None:
            log_game_event(
                "assign_roles_noop",
                chat_id=chat_id,
            )
            return
        try:
            await self._assign_fn(chat_id)
        except RoleBalanceError:
            log_game_event(
                "assign_roles_failed",
                chat_id=chat_id,
            )
            raise
        log_game_event(
            "assign_roles_ok",
            chat_id=chat_id,
        )
