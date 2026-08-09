"""Tick AI agents for active midgame chats."""

from __future__ import annotations

import json
from typing import Any

from AI.actions import AiActions
from AI.context import GameContext
from AI.registry import AgentRegistry
from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event


async def tick_ai_agents(bridge: ChatBridge) -> None:
    """Run AI night/day/vote actions (chat via AI bot)."""
    settings = get_settings()
    if not settings.enable_bot_to_bot:
        return
    keys = RedisKeySpace()
    redis = await get_redis()
    ctx = GameContext(keys)
    acts = AiActions(bridge, keys)
    registry = AgentRegistry()
    for active, phase in (
        (keys.active_night_chats(), "night"),
        (keys.active_day_chats(), "day"),
        (keys.active_vote_chats(), "vote"),
    ):
        chats = await redis.smembers(active)
        for item in chats:
            await _run_chat(
                int(item),
                phase,
                ctx,
                acts,
                registry,
                keys,
            )


async def _run_chat(
    chat_id: int,
    phase: str,
    ctx: GameContext,
    acts: AiActions,
    registry: AgentRegistry,
    keys: RedisKeySpace,
) -> None:
    """Process all AI seats for one chat/phase."""
    redis = await get_redis()
    for uid in await ctx.ai_ids(chat_id):
        snap = await ctx.snapshot(chat_id, uid)
        if snap is None:
            continue
        name = _name_of(snap, uid)
        agent = registry.create(uid, name)
        if phase == "night":
            await _night(
                chat_id, uid, agent, snap, acts, keys
            )
        elif phase == "day":
            await _day(
                chat_id, uid, agent, snap, acts, keys
            )
        else:
            await _vote(
                chat_id, uid, agent, snap, acts, keys
            )
        pending = await redis.hget(
            keys.game_flags(chat_id),
            keys.field("sheriff_shot_pending"),
        )
        if pending and int(pending) == uid:
            target = agent.decide_sheriff_shot(snap)
            if target is not None:
                await acts.sheriff_shot(
                    chat_id,
                    uid,
                    target,
                )


async def _night(
    chat_id: int,
    uid: int,
    agent: Any,
    snap: dict[str, Any],
    acts: AiActions,
    keys: RedisKeySpace,
) -> None:
    """Submit night action if missing."""
    redis = await get_redis()
    if await redis.hget(
        keys.night_actions(chat_id),
        str(uid),
    ):
        return
    choice = agent.decide_night(snap)
    if choice is None:
        return
    await acts.night(chat_id, uid, choice)


async def _day(
    chat_id: int,
    uid: int,
    agent: Any,
    snap: dict[str, Any],
    acts: AiActions,
    keys: RedisKeySpace,
) -> None:
    """Submit day action if missing."""
    redis = await get_redis()
    if await redis.hget(
        keys.day_actions(chat_id),
        str(uid),
    ):
        return
    choice = agent.decide_day(snap)
    if choice is None:
        return
    await acts.day(
        chat_id,
        uid,
        str(snap.get("role_id") or ""),
        choice,
        _name_of(snap, uid),
    )


async def _vote(
    chat_id: int,
    uid: int,
    agent: Any,
    snap: dict[str, Any],
    acts: AiActions,
    keys: RedisKeySpace,
) -> None:
    """Cast vote if this AI has not voted."""
    redis = await get_redis()
    ballots = await redis.hgetall(
        keys.vote_ballots(chat_id)
    )
    for raw in ballots.values():
        voters = {int(v) for v in json.loads(raw)}
        if uid in voters:
            return
    target = agent.decide_vote(snap)
    if target is None:
        return
    await acts.vote(chat_id, uid, target)
    log_game_event(
        "ai_tick_vote",
        chat_id=chat_id,
        user_id=uid,
        target=target,
    )


def _name_of(snap: dict[str, Any], uid: int) -> str:
    """Resolve display name from snapshot."""
    for item in snap.get("players", []):
        if int(item["user_id"]) == uid:
            return str(item.get("fullname", uid))
    return str(uid)
