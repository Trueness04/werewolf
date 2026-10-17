"""Finish vote: plurality + trouble second round."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.text_managers import TextManager


async def finish_vote_round(
    *,
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    lang: str,
    chat_id: int,
    lynch: Any,
    start_vote: Any,
) -> None:
    """Lynch first; then optional trouble second vote."""
    redis = await get_redis()
    await redis.srem(
        keys.active_vote_chats(),
        str(chat_id),
    )
    ballots = await redis.hgetall(
        keys.vote_ballots(chat_id)
    )
    scores: Counter[int] = Counter()
    for target_s, raw in ballots.items():
        scores[int(target_s)] = len(json.loads(raw))
    winner: int | None = None
    if scores:
        best = max(scores.values())
        tops = [
            tid
            for tid, n in scores.items()
            if n == best
        ]
        if len(tops) == 1:
            winner = tops[0]
    if lynch is None:
        return
    flags = keys.game_flags(chat_id)
    trouble = await redis.hget(
        flags,
        keys.field("trouble"),
    )
    trouble_ok = await redis.hget(
        flags,
        keys.field("trouble_ok"),
    )
    if trouble_ok:
        await redis.hdel(
            flags,
            keys.field("trouble"),
            keys.field("trouble_ok"),
        )
        trouble = None
    need_second = bool(trouble)
    await lynch(
        chat_id,
        winner_id=winner,
        peace=False,
        had_votes=bool(scores),
        defer_night=need_second,
    )
    if not need_second:
        return
    await redis.hset(
        flags,
        keys.field("trouble_ok"),
        "1",
    )
    await redis.hdel(flags, keys.field("trouble"))
    await bridge.send_text(
        chat_id,
        texts.get(
            "troubleSecondVote",
            lang,
            bundle="vote",
        ),
    )
    await start_vote(chat_id, bump_day=False)
