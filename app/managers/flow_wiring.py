"""Wire role distribution into Initial Flow."""

from __future__ import annotations

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.lobby_manager import LobbyManager
from app.managers.night_manager import NightManager
from app.managers.role_distribution_manager import (
    RoleDistributionManager,
)
from app.managers.role_setup_manager import (
    RoleSetupManager,
)


def wire_role_assignment(
    bridge: ChatBridge,
    roles: RoleSetupManager,
) -> None:
    """Attach default distribute_roles assign hook."""

    async def _assign(chat_id: int) -> None:
        keys = RedisKeySpace()
        redis = await get_redis()
        key = keys.game_hash(chat_id)
        mode = str(
            await redis.hget(
                key,
                keys.field("game_mode"),
            )
            or "Normal"
        )
        players = await LobbyManager().list_players(
            chat_id,
        )
        night = NightManager(bridge)
        dist = RoleDistributionManager()
        dist.set_night_starter(night.start_first_night)
        await dist.distribute_roles(
            chat_id,
            mode,
            players,
        )
        from app.managers.session_senior import (
            ensure_senior_at_start,
        )

        await ensure_senior_at_start(
            chat_id,
            players,
            bridge=bridge,
        )

    roles.set_assign_hook(_assign)
