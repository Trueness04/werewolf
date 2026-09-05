"""GamedEnd: announce winner and clear session."""

from __future__ import annotations

import json
from time import time

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import WIN_CODES
from app.config.settings import Settings, get_settings
from app.database.models.game import GameRow
from app.database.session import session_scope
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.text_managers import TextManager
from app.managers.win_census import WinCensus


class EndGameManager:
    """Close a running game with a winner code."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace | None = None,
        texts: TextManager | None = None,
        settings: Settings | None = None,
        census: WinCensus | None = None,
    ) -> None:
        self._bridge = bridge
        self._keys = keys or RedisKeySpace()
        self._texts = texts or TextManager()
        self._settings = settings or get_settings()
        self._census = census or WinCensus(self._keys)
        self._codes = load_json(WIN_CODES)

    async def is_ended(self, chat_id: int) -> bool:
        """True when GameIsEnd flag is set."""
        redis = await get_redis()
        raw = await redis.hget(
            self._keys.game_flags(chat_id),
            self._keys.field("game_is_end"),
        )
        return bool(raw)

    async def end(
        self,
        chat_id: int,
        winner: str,
    ) -> None:
        """Announce, flag end, wipe live session."""
        redis = await get_redis()
        if await self.is_ended(chat_id):
            return
        await redis.hset(
            self._keys.game_flags(chat_id),
            self._keys.field("game_is_end"),
            winner,
        )
        lang = self._settings.default_lang
        await self._announce(chat_id, winner, lang)
        await self._record_player_rewards(chat_id, winner)
        await self._mark_db(chat_id, winner)
        await self._cleanup(chat_id)
        log_game_event(
            "game_ended",
            chat_id=chat_id,
            winner=winner,
        )

    async def _announce(
        self,
        chat_id: int,
        winner: str,
        lang: str,
    ) -> None:
        """Send win-list FIRST, then victory GIF+caption (Amin 0905)."""
        bundle = str(self._codes["bundle"])
        captions = self._codes["caption_keys"]
        key = str(captions.get(winner, "winner_nothing"))
        # Win-list BEFORE redis wipe: all seats, roles
        # revealed, win/lose per player (Amin 0904).
        from app.managers.player_format import (
            load_game_players,
            send_win_list,
        )

        players = await load_game_players(chat_id)
        await send_win_list(
            self._bridge,
            self._texts,
            chat_id,
            lang,
            players,
            winner,
        )
        # Victory animation + caption — after the list.
        gifs = self._codes.get("win_gifs", {})
        gif = str(gifs.get(winner, "") or "")
        if gif:
            await self._bridge.send_animation(
                chat_id,
                gif,
                self._texts.get(key, lang, bundle=bundle),
            )
        else:
            await self._bridge.send_text(
                chat_id,
                self._texts.get(key, lang, bundle=bundle),
            )

    async def kill(
        self,
        chat_id: int,
        by_user_id: int | None = None,
    ) -> bool:
        """Admin force-stop; wipe session without win."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        if not await redis.exists(key):
            await self._cleanup(chat_id)
            return False
        lang = self._settings.default_lang
        await redis.hset(
            self._keys.game_flags(chat_id),
            self._keys.field("game_is_end"),
            "killed",
        )
        await self._bridge.send_text(
            chat_id,
            self._texts.get(
                "game_killed",
                lang,
                bundle="lobby",
            ),
        )
        await self._mark_db(chat_id, "killed")
        await self._cleanup(chat_id)
        log_game_event(
            "game_killed",
            chat_id=chat_id,
            user_id=by_user_id,
        )
        return True

    async def _record_player_rewards(
        self,
        chat_id: int,
        winner: str,
    ) -> None:
        """Stats + achievements before Redis wipe."""
        from app.managers.achievement_rewards import (
            apply_end_stats,
        )

        await apply_end_stats(
            chat_id,
            winner,
            keys=self._keys,
            bridge=self._bridge,
            texts=self._texts,
            lang=self._settings.default_lang,
        )
    async def _mark_db(
        self,
        chat_id: int,
        winner: str,
    ) -> None:
        """Persist ended status on GameRow."""
        redis = await get_redis()
        game_id = int(
            await redis.hget(
                self._keys.game_hash(chat_id),
                self._keys.field("game_id"),
            )
            or "0"
        )
        async with session_scope() as session:
            stmt = select(GameRow).where(
                GameRow.id == game_id
            )
            row = (
                await session.execute(stmt)
            ).scalar_one_or_none()
            if row is not None:
                row.status = "ended"
                row.state = winner

    async def _cleanup(self, chat_id: int) -> None:
        """Remove live Redis keys and active sets."""
        redis = await get_redis()
        players_raw = await redis.get(
            self._keys.game_players(chat_id)
        )
        players = (
            json.loads(players_raw) if players_raw else []
        )
        for item in players:
            uid = int(item["user_id"])
            await redis.delete(
                self._keys.player_state(uid)
            )
            await redis.delete(
                self._keys.player_role(uid)
            )
            await redis.delete(self._keys.join_user(uid))
        for method in (
            self._keys.game_hash,
            self._keys.game_players,
            self._keys.game_roles,
            self._keys.night_actions,
            self._keys.day_actions,
            self._keys.day_sent,
            self._keys.vote_ballots,
            self._keys.vote_sent,
            self._keys.night_sent,
            self._keys.role_intro_sent,
            self._keys.game_flags,
            self._keys.ai_players,
            self._keys.ai_personas,
            self._keys.ai_chat_queue,
            self._keys.ai_chat_count,
            self._keys.night_count,
            self._keys.day_count,
            self._keys.timer_end,
        ):
            await redis.delete(method(chat_id))
        for active in (
            self._keys.active_join_chats(),
            self._keys.active_night_chats(),
            self._keys.active_day_chats(),
            self._keys.active_vote_chats(),
        ):
            await redis.srem(active, str(chat_id))
