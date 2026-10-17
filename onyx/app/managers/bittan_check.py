"""BittanCheck: delayed gas convert on vote→night."""

from __future__ import annotations

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.convert_player import convert_player
from app.managers.game_event import log_game_event
from app.managers.text_managers import TextManager
from app.config.settings import get_settings

# Sprint-2 maps PHP names → our Redis fields.
_QUEUE = (
    ("convert_enchanter", "role_wolf", "BittenTurned"),
    ("convert_wolf", "role_wolf", "BittenTurned"),
    ("convert_vampire", "role_vampire", "BittenTurnedVampire"),
)


class BittanCheck:
    """Apply delayed bite converts before next night."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace | None = None,
        texts: TextManager | None = None,
    ) -> None:
        self._bridge = bridge
        self._keys = keys or RedisKeySpace()
        self._texts = texts or TextManager()
        self._lang = get_settings().default_lang

    async def run(self, chat_id: int) -> None:
        """Process all three queues; safe Del if gone."""
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        for field, new_role, msg_key in _QUEUE:
            raw = await redis.hget(
                flags,
                self._keys.field(field),
            )
            if not raw:
                continue
            try:
                uid = int(raw)
            except ValueError:
                await redis.hdel(
                    flags,
                    self._keys.field(field),
                )
                continue
            state = await redis.get(
                self._keys.player_state(uid)
            )
            # Player missing or dead → Del only.
            if state is None or state == "dead":
                await redis.hdel(
                    flags,
                    self._keys.field(field),
                )
                log_game_event(
                    "bittan_clear_dead",
                    chat_id=chat_id,
                    user_id=uid,
                    field=field,
                )
                continue
            ok = await convert_player(
                chat_id,
                uid,
                new_role,
                keys=self._keys,
            )
            await redis.hdel(
                flags,
                self._keys.field(field),
            )
            if field == "convert_enchanter":
                await _prune_enchanter(
                    redis,
                    flags,
                    self._keys,
                    uid,
                )
            if not ok:
                continue
            text = self._texts.get(
                msg_key,
                self._lang,
                bundle="results",
            )
            await self._bridge.send_text(uid, text)
            log_game_event(
                "bittan_converted",
                chat_id=chat_id,
                user_id=uid,
                role=new_role,
                field=field,
            )


async def clear_gas_flag(
    chat_id: int,
    user_id: int,
    keys: RedisKeySpace | None = None,
) -> bool:
    """Botanist cure: Del gas flag for user. True if."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    cleared = False
    for name in (
        "convert_enchanter",
        "convert_wolf",
        "convert_vampire",
    ):
        raw = await redis.hget(flags, keys.field(name))
        if raw and str(raw) == str(user_id):
            await redis.hdel(flags, keys.field(name))
            cleared = True
    return cleared


async def _prune_enchanter(
    redis,
    flags: str,
    keys: RedisKeySpace,
    uid: int,
) -> None:
    """Rewrite enchanter_list without converted uid."""
    from app.managers.enchanter_list import (
        dumps,
        parse_list,
        remove_uid,
    )

    field = keys.field("enchanter_list")
    raw = await redis.hget(flags, field)
    cur = remove_uid(parse_list(raw), uid)
    if not cur:
        await redis.hdel(flags, field)
    else:
        await redis.hset(flags, field, dumps(cur))
    mark_f = keys.field("enchanter_mark")
    mark = await redis.hget(flags, mark_f)
    if mark and str(mark) == str(uid):
        await redis.hdel(flags, mark_f)

