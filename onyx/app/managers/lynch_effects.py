"""Prince/sheriff/normal death helpers for lynch."""

from __future__ import annotations

import json
from time import time

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import Settings
from app.database.models.player import PlayerRow
from app.database.session import session_scope
from app.keyboards.inline.vote_keyboard import (
    build_sheriff_shot_keyboard,
)
from app.managers.chat_bridge import ChatBridge
from app.managers.text_managers import TextManager
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class LynchEffects:
    """Side-effect helpers used by LynchResolver."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace,
        texts: TextManager,
        settings: Settings,
    ) -> None:
        self._bridge = bridge
        self._keys = keys
        self._texts = texts
        self._settings = settings
        self._registry = _Registry()

    async def prince(
        self,
        chat_id: int,
        winner_id: int,
        lang: str,
    ) -> bool:
        """First prince lynch is a save."""
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        saved = await redis.hget(
            flags,
            self._keys.field("prince_saved"),
        )
        if saved:
            return False
        await redis.hset(
            flags,
            self._keys.field("prince_saved"),
            str(winner_id),
        )
        name = await self._player_name(
            chat_id,
            winner_id,
        )
        await self._bridge.send_text(
            chat_id,
            self._texts.get(
                "prince_saved",
                lang,
                name,
                bundle="vote",
            ),
        )
        return True

    async def black_knight(
        self,
        chat_id: int,
        winner_id: int,
        lang: str,
    ) -> bool:
        """First two black-knight lynches are saves."""
        _ = winner_id
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        hits = int(
            await redis.hget(
                flags,
                self._keys.field("black_knight_hits"),
            )
            or "0"
        )
        if hits >= 2:
            return False
        await redis.hset(
            flags,
            self._keys.field("black_knight_hits"),
            str(hits + 1),
        )
        await self._bridge.send_text(
            chat_id,
            self._texts.get(
                "BlackKnightKillVote",
                lang,
                bundle="vote",
            ),
        )
        return True

    async def sheriff(
        self,
        chat_id: int,
        winner_id: int,
        lang: str,
    ) -> bool:
        """Kill sheriff and open death-shot window."""
        role_id = "role_kalantar"
        await self.normal_death(
            chat_id,
            winner_id,
            role_id,
            lang,
        )
        redis = await get_redis()
        await redis.hset(
            self._keys.game_flags(chat_id),
            self._keys.field("sheriff_shot_pending"),
            str(winner_id),
        )
        players = json.loads(
            await redis.get(
                self._keys.game_players(chat_id)
            )
            or "[]"
        )
        targets: list[tuple[int, str]] = []
        for item in players:
            uid = int(item["user_id"])
            if uid == winner_id:
                continue
            state = await redis.get(
                self._keys.player_state(uid)
            )
            if state == "dead":
                continue
            targets.append((uid, str(item["fullname"])))
        markup = build_sheriff_shot_keyboard(
            chat_id,
            winner_id,
            targets,
        )
        await self._bridge.send_text(
            winner_id,
            self._texts.get(
                "sheriff_shot_prompt",
                lang,
                bundle="vote",
            ),
            reply_markup=markup,
        )
        extend = int(
            self._settings.sheriff_shot_seconds
        )
        await redis.set(
            self._keys.timer_end(chat_id),
            str(int(time()) + extend),
        )
        await redis.sadd(
            self._keys.active_vote_chats(),
            str(chat_id),
        )
        return True

    async def normal_death(
        self,
        chat_id: int,
        winner_id: int,
        role_id: str,
        lang: str,
    ) -> None:
        """Standard lynch death + role reveal."""
        await self.mark_dead(chat_id, winner_id)
        name = await self._player_name(
            chat_id,
            winner_id,
            mention=True,
        )
        role_name = role_id
        if role_id:
            mk = self._registry.definition(role_id)[
                "message_keys"
            ]["name"]
            role_name = self._texts.get(
                str(mk),
                lang,
                bundle="roles",
            )
        role_line = self._texts.get(
            "user_role",
            lang,
            role_name,
            bundle="vote",
        )
        await self._bridge.send_text(
            chat_id,
            self._texts.get(
                "killed_user",
                lang,
                name,
                role_line,
                bundle="vote",
            ),
        )
        await self._bridge.send_text(
            winner_id,
            self._texts.get(
                "you_died_lynch",
                lang,
                role_name,
                bundle="vote",
            ),
        )

    async def _player_name(
        self,
        chat_id: int,
        user_id: int,
        *,
        mention: bool = False,
    ) -> str:
        """Resolve display name for a player id."""
        redis = await get_redis()
        players = json.loads(
            await redis.get(
                self._keys.game_players(chat_id)
            )
            or "[]"
        )
        for item in players:
            if int(item["user_id"]) != user_id:
                continue
            raw = str(item["fullname"])
            if not mention:
                return raw
            from app.managers.player_format import (
                mention_html,
            )

            return mention_html(user_id, raw)
        return str(user_id)

    async def mark_dead(
        self,
        chat_id: int,
        user_id: int,
    ) -> None:
        """Persist death in Redis + PostgreSQL."""
        redis = await get_redis()
        await redis.set(
            self._keys.player_state(user_id),
            "dead",
        )
        key = self._keys.game_hash(chat_id)
        game_id = int(
            await redis.hget(
                key,
                self._keys.field("game_id"),
            )
            or "0"
        )
        async with session_scope() as session:
            stmt = select(PlayerRow).where(
                PlayerRow.game_id == game_id,
                PlayerRow.user_id == user_id,
            )
            row = (
                await session.execute(stmt)
            ).scalar_one_or_none()
            if row is not None:
                row.alive = False
                row.state = "dead"
