"""Immediate day-role effects (peace/mayor/...)."""

from __future__ import annotations

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.text_managers import TextManager


class DayActions:
    """Apply one-shot day flags immediately."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace | None = None,
        texts: TextManager | None = None,
    ) -> None:
        self._bridge = bridge
        self._keys = keys or RedisKeySpace()
        self._texts = texts or TextManager()

    async def apply_immediate(
        self,
        chat_id: int,
        user_id: int,
        role_id: str,
        choice: str,
        lang: str,
        fullname: str,
    ) -> str:
        """Handle yes/no immediate roles; return ack key."""
        if choice != "yes":
            return "SelectOk_no"
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        used_map = {
            "role_Solh": "peace_used",
            "role_Ahangar": "silver_used",
            "role_KhabGozar": "sleep_used",
        }
        used_key = used_map.get(role_id)
        if used_key and await redis.hget(
            flags,
            self._keys.field(used_key),
        ):
            return "SelectOk_no"
        if role_id == "role_Solh":
            await redis.hset(
                flags,
                mapping={
                    self._keys.field("peace_flag"): "1",
                    self._keys.field("peace_used"): "1",
                },
            )
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "solh_announce",
                    lang,
                    fullname,
                    bundle="day",
                ),
            )
        elif role_id == "role_Kadkhoda":
            if await redis.hget(
                flags,
                self._keys.field("mayor_revealed"),
            ):
                return "SelectOk_no"
            await redis.hset(
                flags,
                self._keys.field("mayor_revealed"),
                str(user_id),
            )
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "Kadkhoda_announce",
                    lang,
                    fullname,
                    bundle="day",
                ),
            )
        elif role_id == "role_Ahangar":
            await redis.hset(
                flags,
                mapping={
                    self._keys.field(
                        "silver_next_night"
                    ): "1",
                    self._keys.field("silver_used"): "1",
                },
            )
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "ahangar_announce",
                    lang,
                    bundle="day",
                ),
            )
        elif role_id == "role_KhabGozar":
            await redis.hset(
                flags,
                mapping={
                    self._keys.field(
                        "sleep_next_night"
                    ): "1",
                    self._keys.field("sleep_used"): "1",
                },
            )
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "KHABGOZAR_announce",
                    lang,
                    bundle="day",
                ),
            )
        else:
            return "SelectOk_no"
        log_game_event(
            "day_immediate",
            chat_id=chat_id,
            user_id=user_id,
            role=role_id,
        )
        return "SelectOk"
