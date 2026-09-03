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
_log = None


def _L():
    global _log
    if _log is None:
        from app.managers.logger_manager \
            import get_logger
        _log = get_logger()
    return _log


@asynccontextmanager
async def _chat_lock(keys, chat_id):
    redis = await get_redis()
    lock_key = (
        f"{keys.game_flags(chat_id)}:lock"
    )
    got = await redis.set(
        lock_key, "1", nx=True, ex=_LOCK_TTL,
    )
    if not got:
        yield False
        return
    try:
        yield True
    finally:
        await redis.delete(lock_key)


async def tick_end_checks(bridge):
    keys = RedisKeySpace()
    redis = await get_redis()
    judge = WinJudge(keys)
    ender = EndGameManager(bridge, keys)
    chats = set()
    for active in (
        keys.active_night_chats(),
        keys.active_day_chats(),
        keys.active_vote_chats(),
    ):
        chats.update(await redis.smembers(active))
    L = _L()
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
            L.info(
                "end_check hit={} w={}",
                chat_id, winner,
            )
            await ender.end(chat_id, winner)


async def tick_active_nights(bridge):
    keys = RedisKeySpace()
    redis = await get_redis()
    ender = EndGameManager(bridge, keys)
    chats = await redis.smembers(
        keys.active_night_chats(),
    )
    night = NightManager(bridge)
    resolver = NightResolver(bridge)
    L = _L()
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
                L.debug(
                    "night SKIP ended={}",
                    chat_id,
                )
                continue
            if not await night.tick_night(
                chat_id,
            ):
                L.debug(
                    "night WAIT={}",
                    chat_id,
                )
                continue
            await redis.srem(
                keys.active_night_chats(),
                str(chat_id),
            )
            log_game_event(
                "night_timer_end",
                chat_id=chat_id,
            )
            held = await resolver.resolve(
                chat_id,
            )
            L.info(
                "night DONE={} held={}",
                chat_id, held,
            )
            if held:
                continue


async def tick_active_days(bridge):
    keys = RedisKeySpace()
    redis = await get_redis()
    ender = EndGameManager(bridge, keys)
    chats = await redis.smembers(
        keys.active_day_chats(),
    )
    day, resolver, _vote = \
        build_day_pipeline(bridge)
    L = _L()
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
                L.debug(
                    "day SKIP ended={}",
                    chat_id,
                )
                continue
            if not await day.tick_day(
                chat_id,
            ):
                L.debug(
                    "day WAIT={}",
                    chat_id,
                )
                continue
            flags = keys.game_flags(
                chat_id,
            )
            pending = await redis.hget(
                flags,
                keys.field(
                    "sheriff_shot_pending",
                ),
            )
            source = await redis.hget(
                flags,
                keys.field(
                    "hunter_kill_source",
                ),
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
            L.info("day DONE={}", chat_id)


async def tick_active_votes(bridge):
    keys = RedisKeySpace()
    redis = await get_redis()
    ender = EndGameManager(bridge, keys)
    chats = await redis.smembers(
        keys.active_vote_chats(),
    )
    _day, _res, vote = \
        build_day_pipeline(bridge)
    texts = TextManager()
    lang = get_settings().default_lang
    L = _L()
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
                L.debug(
                    "vote SKIP ended={}",
                    chat_id,
                )
                continue
            if not await vote.tick_vote(
                chat_id,
            ):
                L.debug(
                    "vote WAIT={}",
                    chat_id,
                )
                continue
            flags = keys.game_flags(
                chat_id,
            )
            pending = await redis.hget(
                flags,
                keys.field(
                    "sheriff_shot_pending",
                ),
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
                flags,
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
            dn = await redis.hget(
                flags,
                keys.field(
                    "darneshan_pick_pending",
                ),
            )
            if dn:
                from app.managers \
                    .darneshan_resolve import (
                    timeout_darneshan_pick,
                )
                lynch = LynchResolver(bridge)
                night = NightManager(bridge)
                lynch.set_night_starter(
                    night.start_night,
                )
                await timeout_darneshan_pick(
                    bridge,
                    keys,
                    texts,
                    lang,
                    chat_id,
                    int(dn),
                    lynch._to_night,
                )
                continue
            log_game_event(
                "vote_timer_end",
                chat_id=chat_id,
            )
            await vote.finish_vote(chat_id)
            L.info("vote DONE={}", chat_id)


async def _sheriff_timeout(
    bridge, keys, texts, lang,
    chat_id, sheriff_id,
):
    redis = await get_redis()
    raw = await redis.get(
        keys.game_players(chat_id),
    )
    players = json.loads(raw) if raw else []
    name = next(
        (
            r["fullname"]
            for r in players
            if int(r["user_id"]) == sheriff_id
        ),
        str(sheriff_id),
    )
    msg = texts.get(
        "sheriff_shot_skip",
        lang,
        name,
        bundle="vote",
    )
    await bridge.send_text(chat_id, msg)
    lynch = LynchResolver(bridge)
    night = NightManager(bridge)
    lynch.set_night_starter(night.start_night)
    await lynch.continue_after_shot_timeout(
        chat_id,
    )


async def _stop_black_timeout(
    bridge, keys, texts, lang,
    chat_id, actor_id,
):
    redis = await get_redis()
    raw = await redis.get(
        keys.game_players(chat_id),
    )
    players = json.loads(raw) if raw else []
    name = next(
        (
            r["fullname"]
            for r in players
            if int(r["user_id"]) == actor_id
        ),
        str(actor_id),
    )
    msg = texts.get(
        "StopBlackSkip",
        lang,
        name,
        bundle="vote",
    )
    await bridge.send_text(chat_id, msg)
    lynch = LynchResolver(bridge)
    night = NightManager(bridge)
    lynch.set_night_starter(night.start_night)
    await lynch.continue_after_black_timeout(
        chat_id,
    )
