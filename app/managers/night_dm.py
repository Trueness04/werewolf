"""Night role DM delivery helpers."""

from __future__ import annotations

from typing import Any

from app.cache.redis_client import get_redis
from app.managers.logger_manager import get_logger
from app.cache.redis_keys import RedisKeySpace
from app.keyboards.inline.night_keyboard import (
    build_target_keyboard,
    build_yes_no_keyboard,
)
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.text_managers import TextManager
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class NightDmSender:
    """Send role intro and night action prompts."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace | None = None,
        texts: TextManager | None = None,
    ) -> None:
        self._bridge = bridge
        self._keys = keys or RedisKeySpace()
        self._texts = texts or TextManager()
        self._registry = _Registry()

    async def send_role_dm(
        self,
        chat_id: int,
        player: dict[str, Any],
        lang: str,
        all_players: list[dict[str, Any]],
    ) -> None:
        """Send role intro once + per-night action prompt."""
        log = get_logger()
        uid = int(player["user_id"])
        redis = await get_redis()
        sent_key = self._keys.night_sent(chat_id)
        already = await redis.sismember(sent_key, str(uid))
        log.info(
            "role_dm_check uid={} sent={}",
            uid, already,
        )
        if already:
            return
        role_id = str(player.get("role") or "")
        if not role_id:
            return
        role = self._registry.create(role_id)
        intro_key = self._keys.role_intro_sent(chat_id)
        already_intro = await redis.sismember(
            intro_key,
            str(uid),
        )
        if not already_intro:
            await self._send_intro(
                chat_id,
                uid,
                role,
                lang,
                all_players,
            )
            await redis.sadd(intro_key, str(uid))
        await self._maybe_send_magic(
            chat_id,
            uid,
            lang,
        )
        if role.night1_active:
            if not await self._skip_action(
                chat_id,
                uid,
                role,
            ):
                await self._send_action(
                    chat_id,
                    uid,
                    role,
                    lang,
                    all_players,
                )
        await redis.sadd(sent_key, str(uid))

    async def _send_intro(
        self,
        chat_id: int,
        uid: int,
        role: Any,
        lang: str,
        all_players: list[dict[str, Any]],
    ) -> None:
        """Build and send one-time role intro body."""
        mk = role.message_keys
        name = self._texts.get(
            str(mk["name"]),
            lang,
            bundle="roles",
        )
        desc = self._texts.get(
            str(mk["description"]),
            lang,
            bundle="roles",
        )
        body = f"{name}\n{desc}"
        team_key = mk.get("team_info")
        if team_key:
            mates = [
                str(p["fullname"])
                for p in all_players
                if p.get("team") == role.team
                and int(p["user_id"]) != uid
                and p.get("alive", True)
            ]
            body = (
                f"{body}\n"
                + self._texts.get(
                    str(team_key),
                    lang,
                    ", ".join(mates),
                    bundle="roles",
                )
            )
        await self._bridge.send_text(uid, body)
        log_game_event(
            "role_dm_sent",
            chat_id=chat_id,
            user_id=uid,
            role=role.role_id,
        )

    async def _maybe_send_magic(
        self,
        chat_id: int,
        uid: int,
        lang: str,
    ) -> None:
        """Send magic panel if inventory > 0 and allowed."""
        from app.keyboards.inline.magic_keyboard import (
            build_magic_keyboard,
        )
        from app.managers.magic_effects import magic_allowed
        from app.managers.magic_inventory import (
            inventory_counts,
            total_magic,
        )

        if not await magic_allowed(chat_id, self._keys):
            return
        if await total_magic(uid) < 1:
            return
        counts = await inventory_counts(uid)
        await self._bridge.send_text(
            uid,
            self._texts.get("MajikPanelMsg", lang),
            reply_markup=build_magic_keyboard(
                self._texts,
                lang,
                chat_id,
                counts=counts,
            ),
        )

    async def _skip_action(
        self,
        chat_id: int,
        uid: int,
        role: Any,
    ) -> bool:
        """Sprint-01 SendNightRole skip gates."""
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        iced = await redis.hget(
            flags,
            self._keys.field("player_iced"),
        )
        if iced and str(iced) == str(uid):
            return True
        if role.role_id == "role_Mummy":
            die = await redis.hget(
                flags,
                self._keys.field("die_cult"),
            )
            if not die:
                return True
        blood = await redis.hget(
            flags,
            self._keys.field("blood_moon_active"),
        )
        if blood:
            from app.managers.bloodmoon import (
                BLOOD_MOON_ALLOWED_ROLES,
            )

            if role.role_id not in BLOOD_MOON_ALLOWED_ROLES:
                if role.night1_active:
                    return True
        if role.team != "wolf":
            return False
        if role.role_id in {
            "role_WhiteWolf",
            "role_mighty_white_wolf",
        }:
            return False
        mast = await redis.hget(
            flags,
            self._keys.field("mast_block"),
        )
        silver = await redis.hget(
            flags,
            self._keys.field("silver_active"),
        )
        return bool(mast or silver)

    async def _send_action(
        self,
        chat_id: int,
        uid: int,
        role: Any,
        lang: str,
        all_players: list[dict[str, Any]],
    ) -> None:
        """Send night prompt + keyboard by target_type."""
        mk = role.message_keys
        prompt_key = mk.get("night_prompt")
        prompt = ""
        if prompt_key:
            prompt = self._texts.get(
                str(prompt_key),
                lang,
                bundle="roles",
            )
        ttype = role.target_type
        markup = None
        if ttype == "single_target":
            from app.managers.special_teams import (
                alive_targets_hide_bride,
            )

            targets = alive_targets_hide_bride(
                all_players,
                uid,
            )
            # Hide magic-ghost players from night lists
            from app.managers.magic_targets import (
                without_magic_ghosts,
            )

            targets = await without_magic_ghosts(
                chat_id,
                targets,
                self._keys,
            )
            if role.role_id == "role_DarNeshan":
                from app.managers.darneshan_resolve import (
                    cult_mongo_roles,
                )

                cult = cult_mongo_roles()
                targets = [
                    t
                    for t in targets
                    if not any(
                        int(p["user_id"]) == t[0]
                        and (
                            str(p.get("role") or "") in cult
                            or str(p.get("role") or "")
                            == "role_BrideTheDead"
                        )
                        for p in all_players
                    )
                ]
            # SK cannot target Archer
            if role.role_id == "role_Qatel":
                targets = [
                    t
                    for t in targets
                    if not any(
                        int(p["user_id"]) == t[0]
                        and p.get("role") == "role_Archer"
                        for p in all_players
                    )
                ]
            if role.role_id == "role_Archer":
                targets = [
                    t
                    for t in targets
                    if not any(
                        int(p["user_id"]) == t[0]
                        and p.get("role") == "role_Qatel"
                        for p in all_players
                    )
                ]
            markup = build_target_keyboard(
                chat_id,
                uid,
                targets,
            )
        elif ttype == "yes_no":
            markup = build_yes_no_keyboard(
                self._texts,
                lang,
                chat_id,
                uid,
                str(mk.get("button_yes")),
                str(mk.get("button_no")),
            )
        if prompt or markup:
            await self._bridge.send_text(
                uid,
                prompt or role.role_id,
                reply_markup=markup,
            )
