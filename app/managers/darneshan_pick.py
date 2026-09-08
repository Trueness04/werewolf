"""Darneshan pick open/apply (split of darneshan_resolve)."""

from __future__ import annotations

from time import time

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import ROOT
from app.managers.chat_bridge import ChatBridge
from app.managers.convert_player import (
    convert_player,
)
from app.managers.cult_helpers import cult_rules
from app.managers.json_loader import load_json
from app.managers.text_managers import TextManager


async def maybe_open_darneshan_pick(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    settings,
    chat_id: int,
    lynched_id: int,
    lang: str,
) -> bool:
    """Open convert pick if lynched was marked. True=hold."""
    from app.managers.darneshan_resolve import (
        _CHANCES,
        _clear_mark_redis,
        cult_mongo_roles,
    )

    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    mark = await redis.hget(
        flags,
        keys.field("darneshan_mark_target"),
    )
    marker = await redis.hget(
        flags,
        keys.field("darneshan_mark_by"),
    )
    if not mark or not marker:
        return False
    if int(mark) != lynched_id:
        return False
    marker_id = int(marker)
    state = await redis.get(
        keys.player_state(marker_id)
    )
    if state == "dead":
        await _clear_mark_redis(
            redis, keys, chat_id
        )
        return False
    roles = json.loads(
        await redis.get(
            keys.game_roles(chat_id)
        )
        or "{}"
    )
    if (
        str(roles.get(str(marker_id), ""))
        != "role_DarNeshan"
    ):
        await _clear_mark_redis(
            redis, keys, chat_id
        )
        return False
    players = json.loads(
        await redis.get(
            keys.game_players(chat_id)
        )
        or "[]"
    )
    cult = cult_mongo_roles()
    targets = []
    for item in players:
        uid = int(item["user_id"])
        if uid in {lynched_id, marker_id}:
            continue
        if (
            await redis.get(
                keys.player_state(uid)
            )
            == "dead"
        ):
            continue
        role = str(
            roles.get(str(uid), "")
        )
        if role in cult:
            continue
        if role == "role_BrideTheDead":
            continue
        targets.append(
            (uid, str(item["fullname"]))
        )
    if not targets:
        await bridge.send_text(
            marker_id,
            texts.get(
                "DarNeshanPickNoTarget",
                lang,
                bundle="vote",
            ),
        )
        await _clear_mark_redis(
            redis, keys, chat_id
        )
        return False
    dead_name = str(lynched_id)
    for item in players:
        if int(item["user_id"]) == lynched_id:
            dead_name = str(
                item["fullname"]
            )
            break
    from app.keyboards.inline.vote_keyboard import (
        build_darneshan_pick_keyboard,
    )

    markup = build_darneshan_pick_keyboard(
        chat_id,
        marker_id,
        targets,
    )
    await bridge.send_text(
        marker_id,
        texts.get(
            "DarNeshanPickAsk",
            lang,
            dead_name,
            bundle="vote",
        ),
        reply_markup=markup,
    )
    await redis.hset(
        flags,
        keys.field("darneshan_pick_pending"),
        str(marker_id),
    )
    secs = int(
        load_json(_CHANCES).get(
            "darneshan_pick_seconds",
            getattr(
                settings,
                "sheriff_shot_seconds",
                45,
            ),
        )
    )
    await redis.set(
        keys.timer_end(chat_id),
        str(int(time()) + secs),
    )
    await redis.sadd(
        keys.active_vote_chats(),
        str(chat_id),
    )
    return True


async def apply_darneshan_pick(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    chat_id: int,
    actor_id: int,
    target_id: int,
    lang: str,
    to_night,
) -> None:
    """Convert pick target to ferqe then continue night."""
    from app.managers.darneshan_resolve import (
        _CHANCES,
        _clear_mark_redis,
        cult_mongo_roles,
    )

    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    pending = await redis.hget(
        flags,
        keys.field("darneshan_pick_pending"),
    )
    if not pending or int(pending) != actor_id:
        return
    roles = json.loads(
        await redis.get(
            keys.game_roles(chat_id)
        )
        or "{}"
    )
    cult = cult_mongo_roles()
    trole = str(
        roles.get(str(target_id), "")
    )
    if (
        await redis.get(
            keys.player_state(target_id)
        )
        == "dead"
        or target_id == actor_id
        or trole in cult
    ):
        await bridge.send_text(
            actor_id,
            texts.get(
                "DarNeshanPickInvalid",
                lang,
                bundle="vote",
            ),
        )
        return
    mark = await redis.hget(
        flags,
        keys.field("darneshan_mark_target"),
    )
    dead_name = str(mark or "")
    players = json.loads(
        await redis.get(
            keys.game_players(chat_id)
        )
        or "[]"
    )
    target_name = str(target_id)
    for item in players:
        uid = int(item["user_id"])
        if (
            mark
            and uid == int(mark)
        ):
            dead_name = str(
                item["fullname"]
            )
        if uid == target_id:
            target_name = str(
                item["fullname"]
            )
    await convert_player(
        chat_id, target_id, "role_ferqe"
    )
    for gas in (
        "convert_wolf",
        "convert_vampire",
        "convert_enchanter",
    ):
        cur = await redis.hget(
            flags,
            keys.field(gas),
        )
        if cur and str(cur) == str(target_id):
            await redis.hdel(
                flags, keys.field(gas)
            )
    await bridge.send_text(
        target_id,
        texts.get(
            "DarNeshanConvertYou",
            lang,
            dead_name,
            bundle="vote",
        ),
    )
    for item in players:
        uid = int(item["user_id"])
        if (
            await redis.get(
                keys.player_state(uid)
            )
            == "dead"
        ):
            continue
        role = str(roles.get(str(uid), ""))
        if role not in cult or uid != actor_id:
            continue
        if uid == target_id:
            continue
        await bridge.send_text(
            uid,
            texts.get(
                "DarNeshanCultJoin",
                lang,
                dead_name,
                target_name,
                bundle="vote",
            ),
        )
    await redis.hdel(
        flags,
        keys.field("darneshan_pick_pending"),
        keys.field("darneshan_mark_target"),
        keys.field("darneshan_mark_by"),
        keys.field("darneshan_mark_night"),
    )
    await to_night(chat_id)
