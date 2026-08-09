"""Immediate day-role effects (peace/mayor/...)."""

from __future__ import annotations

import json

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
            "role_trouble": "trouble_used",
            "role_Ruler": "ruler_used",
            "role_davina": "davina_used",
            "role_BeladMoon": "belad_moon_used",
        }
        used_key = used_map.get(role_id)
        if used_key and await redis.hget(
            flags,
            self._keys.field(used_key),
        ):
            return "SelectOk_no"
        if role_id == "role_Solh":
            day_n = int(
                await redis.get(
                    self._keys.day_count(chat_id)
                )
                or "1"
            )
            await redis.hset(
                flags,
                mapping={
                    self._keys.field("peace_flag"): str(
                        day_n + 1
                    ),
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
        elif role_id == "role_trouble":
            await redis.hset(
                flags,
                mapping={
                    self._keys.field("trouble"): "1",
                    self._keys.field("trouble_used"): "1",
                },
            )
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "troubleGroupMessage",
                    lang,
                    fullname,
                    bundle="day",
                ),
            )
        elif role_id == "role_Ruler":
            day_n = int(
                await redis.get(
                    self._keys.day_count(chat_id)
                )
                or "1"
            )
            await redis.hset(
                flags,
                mapping={
                    self._keys.field("ruler_ok"): str(
                        day_n + 1
                    ),
                    self._keys.field("ruler_used"): "1",
                },
            )
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "RulerNowRul",
                    lang,
                    fullname,
                    bundle="day",
                ),
            )
        elif role_id == "role_davina":
            day_n = int(
                await redis.get(
                    self._keys.day_count(chat_id)
                )
                or "1"
            )
            await redis.hset(
                flags,
                mapping={
                    self._keys.field("davina_next"): str(
                        day_n + 1
                    ),
                    self._keys.field("davina_used"): "1",
                },
            )
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "DavinaSilence",
                    lang,
                    fullname,
                    bundle="day",
                ),
            )
        elif role_id == "role_BeladMoon":
            night_n = int(
                await redis.get(
                    self._keys.night_count(chat_id)
                )
                or "0"
            )
            already = await redis.hget(
                flags,
                self._keys.field("belad_moon_used"),
            )
            if already:
                return "BeladMoonAlready"
            await redis.hset(
                flags,
                mapping={
                    self._keys.field(
                        "blood_moon_next_night"
                    ): "1",
                    self._keys.field("blood_moon_night"): str(
                        night_n + 1
                    ),
                    self._keys.field("belad_moon_used"): "1",
                    self._keys.field("belad_moon_by"): str(
                        user_id
                    ),
                },
            )
            await self._bridge.send_text(
                user_id,
                self._texts.get(
                    "BeladMoonAnnouncedSelf",
                    lang,
                    bundle="day",
                ),
            )
            roles = {}
            raw_roles = await redis.get(
                self._keys.game_roles(chat_id)
            )
            if raw_roles:
                roles = json.loads(raw_roles)
            players_raw = await redis.get(
                self._keys.game_players(chat_id)
            )
            players = (
                json.loads(players_raw) if players_raw else []
            )
            vamp_team = {
                "role_vampire",
                "role_BeladMoon",
                "role_chiang",
                "role_Kent",
                "role_Bloodthirsty",
            }
            for item in players:
                uid = int(item["user_id"])
                if uid == user_id:
                    continue
                if str(roles.get(str(uid), "")) not in (
                    vamp_team
                ):
                    continue
                st = await redis.get(
                    self._keys.player_state(uid)
                )
                if st == "dead":
                    continue
                await self._bridge.send_text(
                    uid,
                    self._texts.get(
                        "BeladMoonAnnouncedTeamDay",
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
