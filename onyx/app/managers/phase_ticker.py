"""Unified Redis timer ticks for night/day/vote."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from app.managers.chat_bridge import ChatBridge
from app.managers.end_game_manager import EndGameManager
from app.managers.game_event import log_game_event
from app.managers.lynch_resolver import LynchResolver
from app.managers.night_manager import NightManager
from app.managers.night_resolver import NightResolver
from app.managers.phase_wiring import build_day_pipeline
from app.managers.text_managers import TextManager
from app.managers.win_judge import WinJudge

_LOCK_TTL = 20


@asynccontextmanager
async def _chat_lock(
    keys: RedisKeySpace,
    chat_id: int,
):
    """InComplater-style per-chat tick lock."""
    redis = await get_redis()
    lock_key = f"{keys.game_flags(chat_id)}:lock"
    got = await redis.set(
        lock_key,
        "1",
        nx=True,
        ex=_LOCK_TTL,
    )
    if not got:
        yield False
        return
    try:
        yield True
    finally:
        await redis.delete(lock_key)


async def tick_end_checks(bridge: ChatBridge) -> None:
    """CheckEndGame for all midgame chats each tick."""
    keys = RedisKeySpace()
    redis = await get_redis()
    judge = WinJudge(keys)
    ender = EndGameManager(bridge, keys)
    chats: set[str] = set()
    for active in (
        keys.active_night_chats(),
        keys.active_day_chats(),
        keys.active_vote_chats(),
    ):
        chats.update(await redis.smembers(active))
    for item in chats:
        chat_id = int(item)
        async with _chat_lock(keys, chat_id) as ok:
            if not ok:
                continue
            if await ender.is_ended(chat_id):
                continue
            winner = await judge.check(chat_id)
            if winner is None:
                continue
            log_game_event(
                "end_check_hit",
                chat_id=chat_id,
                winner=winner,
            )
            await ender.end(chat_id, winner)


async def tick_active_nights(bridge: ChatBridge) -> None:
    """Resolve expired nights into day."""
    keys = RedisKeySpace()
    redis = await get_redis()
    ender = EndGameManager(bridge, keys)
    chats = await redis.smembers(
        keys.active_night_chats()
    )
    night = NightManager(bridge)
    resolver = NightResolver(bridge)
    for item in chats:
        chat_id = int(item)
        async with _chat_lock(keys, chat_id) as ok:
            if not ok:
                continue
            if await ender.is_ended(chat_id):
                await redis.srem(
                    keys.active_night_chats(),
                    str(chat_id),
                )
                continue
            if not await night.tick_night(chat_id):
                continue
            await redis.srem(
                keys.active_night_chats(),
                str(chat_id),
            )
            log_game_event(
                "night_timer_end",
                chat_id=chat_id,
            )
            held = await resolver.resolve(chat_id)
            if held:
                continue


async def tick_active_days(bridge: ChatBridge) -> None:
    """Resolve expired days into vote."""
    keys = RedisKeySpace()
    redis = await get_redis()
    ender = EndGameManager(bridge, keys)
    chats = await redis.smembers(keys.active_day_chats())
    day, resolver, _vote = build_day_pipeline(bridge)
    for item in chats:
        chat_id = int(item)
        async with _chat_lock(keys, chat_id) as ok:
            if not ok:
                continue
            if await ender.is_ended(chat_id):
                await redis.srem(
                    keys.active_day_chats(),
                    str(chat_id),
                )
                continue
            if not await day.tick_day(chat_id):
                continue
            pending = await redis.hget(
                keys.game_flags(chat_id),
                keys.field("sheriff_shot_pending"),
            )
            source = await redis.hget(
                keys.game_flags(chat_id),
                keys.field("hunter_kill_source"),
            )
            if pending and source == "day":
                await _sheriff_timeout(
                    bridge,
                    keys,
                    TextManager(),
                    get_settings().default_lang,
                    chat_id,
                    int(pending),
                )
                continue
            log_game_event(
                "day_timer_end",
                chat_id=chat_id,
            )
            await resolver.resolve(chat_id)


async def tick_active_votes(bridge: ChatBridge) -> None:
    """Finish expired votes / sheriff shot window."""
    keys = RedisKeySpace()
    redis = await get_redis()
    ender = EndGameManager(bridge, keys)
    chats = await redis.smembers(
        keys.active_vote_chats()
    )
    _day, _res, vote = build_day_pipeline(bridge)
    texts = TextManager()
    lang = get_settings().default_lang
    for item in chats:
        chat_id = int(item)
        async with _chat_lock(keys, chat_id) as ok:
            if not ok:
                continue
            if await ender.is_ended(chat_id):
                await redis.srem(
                    keys.active_vote_chats(),
                    str(chat_id),
                )
                continue
            if not await vote.tick_vote(chat_id):
                continue
            pending = await redis.hget(
                keys.game_flags(chat_id),
                keys.field("sheriff_shot_pending"),
            )
            if pending:
                await _sheriff_timeout(
                    bridge,
                    keys,
                    texts,
                    lang,
                    chat_id,
                    int(pending),
                )
                continue
            stop_b = await redis.hget(
                keys.game_flags(chat_id),
                keys.field("stop_black"),
            )
            if stop_b:
                await _stop_black_timeout(
                    bridge,
                    keys,
                    texts,
                    lang,
                    chat_id,
                    int(stop_b),
                )
                continue
            dn_pick = await redis.hget(
                keys.game_flags(chat_id),
                keys.field("darneshan_pick_pending"),
            )
            if dn_pick:
                from app.managers.darneshan_resolve import (
                    timeout_darneshan_pick,
                )

                lynch = LynchResolver(bridge)
                night = NightManager(bridge)
                lynch.set_night_starter(
                    night.start_night
                )
                await timeout_darneshan_pick(
                    bridge,
                    keys,
                    texts,
                    lang,
                    chat_id,
                    int(dn_pick),
                    lynch._to_night,
                )
                continue
            log_game_event(
                "vote_timer_end",
                chat_id=chat_id,
            )
            await vote.finish_vote(chat_id)


async def _sheriff_timeout(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    lang: str,
    chat_id: int,
    sheriff_id: int,
) -> None:
    """Announce skip then continue after shot window."""
    redis = await get_redis()
    players_raw = await redis.get(
        keys.game_players(chat_id)
    )
    players = json.loads(players_raw) if players_raw else []
    sheriff_name = str(sheriff_id)
    for row in players:
        if int(row["user_id"]) == sheriff_id:
            sheriff_name = str(row["fullname"])
            break
    await bridge.send_text(
        chat_id,
        texts.get(
            "sheriff_shot_skip",
            lang,
            sheriff_name,
            bundle="vote",
        ),
    )
    lynch = LynchResolver(bridge)
    night = NightManager(bridge)
    lynch.set_night_starter(night.start_night)
    await lynch.continue_after_shot_timeout(chat_id)


async def _stop_black_timeout(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    lang: str,
    chat_id: int,
    actor_id: int,
) -> None:
    """Announce StopBlack skip then go night."""
    redis = await get_redis()
    players_raw = await redis.get(
        keys.game_players(chat_id)
    )
    players = json.loads(players_raw) if players_raw else []
    name = str(actor_id)
    for row in players:
        if int(row["user_id"]) == actor_id:
            name = str(row["fullname"])
            break
    await bridge.send_text(
        chat_id,
        texts.get(
            "StopBlackSkip",
            lang,
            name,
            bundle="vote",
        ),
    )
    lynch = LynchResolver(bridge)
    night = NightManager(bridge)
    lynch.set_night_starter(night.start_night)
    await lynch.continue_after_black_timeout(chat_id)
