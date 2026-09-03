"""AFK DontVote bump and kill after vote→night."""

from __future__ import annotations

import json

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.text_managers import TextManager


def _dont_field(uid: int) -> str:
    return f"dont_vote:{uid}"


async def clear_dont_vote(
    keys: RedisKeySpace,
    chat_id: int,
    user_id: int,
) -> None:
    """Successful vote clears AFK strike."""
    redis = await get_redis()
    await redis.hdel(
        keys.game_flags(chat_id),
        keys.field(_dont_field(user_id)),
    )


async def process_vote_afk(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    chat_id: int,
    lang: str,
) -> None:
    """Bump DontVote for non-voters; kill at 2."""
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    # Ruler day: no AFK strikes this transition.
    if await redis.hget(
        flags,
        keys.field("ruler_ok"),
    ):
        await redis.delete(keys.vote_sent(chat_id))
        return
    # Peace night: skip AFK (flag still set).
    if await redis.hget(
        flags,
        keys.field("peace_flag"),
    ):
        await redis.delete(keys.vote_sent(chat_id))
        return
    ballots = await redis.hgetall(
        keys.vote_ballots(chat_id)
    )
    voted: set[int] = set()
    for raw in ballots.values():
        for vid in json.loads(raw):
            voted.add(int(vid))
    sent = await redis.smembers(keys.vote_sent(chat_id))
    for uid_s in sent:
        uid = int(uid_s)
        if uid in voted:
            continue
        field = keys.field(_dont_field(uid))
        cur = int(await redis.hget(flags, field) or "0")
        await redis.hset(
            flags,
            field,
            str(min(cur + 1, 2)),
        )
    await redis.delete(keys.vote_sent(chat_id))
    players = json.loads(
        await redis.get(keys.game_players(chat_id))
        or "[]"
    )
    roles = json.loads(
        await redis.get(keys.game_roles(chat_id))
        or "{}"
    )
    all_flags = await redis.hgetall(flags)
    for field, raw in all_flags.items():
        if not str(field).startswith("dont_vote:"):
            continue
        if int(raw or "0") < 2:
            continue
        uid = int(str(field).split(":", 1)[1])
        state = await redis.get(keys.player_state(uid))
        if state == "dead":
            await redis.hdel(flags, field)
            continue
        await _kill_afk(
            bridge,
            keys,
            texts,
            chat_id,
            lang,
            uid,
            players,
            roles,
        )
        await redis.hdel(flags, field)
        log_game_event(
            "afk_kill",
            chat_id=chat_id,
            user_id=uid,
        )


async def _kill_afk(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    chat_id: int,
    lang: str,
    uid: int,
    players: list,
    roles: dict,
) -> None:
    redis = await get_redis()
    await redis.set(keys.player_state(uid), "dead")
    name = str(uid)
    for row in players:
        if int(row["user_id"]) == uid:
            name = str(row["fullname"])
            row["alive"] = False
            break
    await redis.set(
        keys.game_players(chat_id),
        json.dumps(players, ensure_ascii=False),
    )
    role_id = str(roles.get(str(uid), ""))
    role_name = role_id or "?"
    await bridge.send_text(
        chat_id,
        texts.get(
            "afkedPlayerMessage",
            lang,
            name,
            role_name,
            bundle="vote",
        ),
    )
