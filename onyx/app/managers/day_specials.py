"""Day special steps: Diane + Botanist (sprint 2/4/5e)."""

from __future__ import annotations

from random import SystemRandom
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.text_managers import TextManager


async def step_diane(
    ctx: dict[str, Any],
    lang: str,
    *,
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager | None = None,
) -> None:
    """Day2 mark+announce; other days 50% see."""
    redis = await get_redis()
    chat_id = int(ctx["chat_id"])
    flags = keys.game_flags(chat_id)
    due = await redis.hget(
        flags,
        keys.field("diane_due_day"),
    )
    target = await redis.hget(
        flags,
        keys.field("diane_target"),
    )
    day_n = int(
        await redis.get(keys.day_count(chat_id)) or "1"
    )
    # Due check → black win
    if due and target:
        if day_n >= int(due):
            state = await redis.get(
                keys.player_state(int(target))
            )
            if state != "dead":
                from app.managers.end_game_manager import (
                    EndGameManager,
                )

                await EndGameManager(bridge).end(
                    chat_id,
                    "black",
                )
                return
        # Still waiting — also process new action below

    raw = None
    actor = None
    for uid, val in (ctx.get("actions") or {}).items():
        role = (ctx.get("roles") or {}).get(str(uid))
        if role == "role_dian":
            raw = val
            actor = int(uid)
            break
    if not raw:
        return
    tid = int(raw)
    state = await redis.get(keys.player_state(tid))
    if state == "dead":
        if actor is not None and texts is not None:
            await bridge.send_text(
                actor,
                texts.get(
                    "DianTargetDead",
                    lang,
                    bundle="day",
                ),
            )
        return
    if day_n == 2:
        await redis.hset(
            flags,
            mapping={
                keys.field("diane_target"): str(tid),
                keys.field("diane_due_day"): str(
                    day_n + 4
                ),
            },
        )
        name = ""
        for p in ctx.get("players") or []:
            if int(p["user_id"]) == tid:
                name = str(p.get("fullname") or tid)
                break
        await bridge.send_text(
            chat_id,
            (texts or TextManager()).get(
                "DianMarkGroup",
                lang,
                name,
                bundle="day",
            ),
        )
        return
    # Other days: 50% see role
    role_id = (ctx.get("roles") or {}).get(str(tid), "")
    if SystemRandom().randrange(100) < 50:
        key = "DianSee"
        arg = role_id
    else:
        key = "DianNotSee"
        arg = None
    if actor is not None:
        tm = texts or TextManager()
        if arg:
            msg = tm.get(key, lang, arg, bundle="day")
        else:
            msg = tm.get(key, lang, bundle="day")
        await bridge.send_text(actor, msg)


async def step_botanist(
    ctx: dict[str, Any],
    lang: str,
    *,
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
) -> None:
    """Botanist day cure clears gas flags."""
    redis = await get_redis()
    chat_id = int(ctx["chat_id"])
    flags = keys.game_flags(chat_id)
    roles = ctx.get("roles") or {}
    actions = ctx.get("actions") or {}
    for uid_s, raw in actions.items():
        uid = int(uid_s)
        if roles.get(str(uid)) != "role_Botanist":
            continue
        tid = int(raw)
        for field in (
            "convert_wolf",
            "convert_vampire",
            "convert_enchanter",
        ):
            marked = await redis.hget(
                flags,
                keys.field(field),
            )
            if marked == str(tid):
                await redis.hdel(flags, keys.field(field))
                await bridge.send_text(
                    uid,
                    texts.get(
                        "BotanistCured",
                        lang,
                        bundle="results",
                    ),
                )


async def step_spy(
    ctx: dict[str, Any],
    lang: str,
    *,
    bridge: ChatBridge,
    texts: TextManager,
) -> None:
    """Spy danger yes/no from village config."""
    from app.config.paths import CONFIG_DATA
    from app.managers.json_loader import load_json

    danger = set(
        load_json(
            CONFIG_DATA / "village_chances.json"
        )["spy_danger_roles"]
    )
    roles = ctx.get("roles") or {}
    for uid_s, role_id in roles.items():
        if role_id != "role_Spy":
            continue
        raw = (ctx.get("actions") or {}).get(uid_s)
        if not raw:
            continue
        t_role = str(roles.get(str(raw)) or "")
        key = (
            "spy_danger"
            if t_role in danger
            else "spy_safe"
        )
        await bridge.send_text(
            int(uid_s),
            texts.get(key, lang, bundle="day"),
        )


async def step_detective(
    ctx: dict[str, Any],
    lang: str,
    *,
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    registry: Any,
) -> None:
    """Detective reveals target role name."""
    from app.cache.redis_client import get_redis

    redis = await get_redis()
    honey = await redis.hget(
        keys.game_flags(int(ctx["chat_id"])),
        keys.field("honey_user"),
    )
    roles = ctx.get("roles") or {}
    for uid_s, role_id in roles.items():
        if role_id != "role_karagah":
            continue
        raw = (ctx.get("actions") or {}).get(uid_s)
        if not raw:
            continue
        t_role = str(roles.get(str(raw)) or "")
        if honey and str(honey) == str(raw):
            t_role = "role_wolf"
        label = t_role
        try:
            mk = registry.definition(t_role)[
                "message_keys"
            ]
            label = texts.get(
                str(mk["name"]),
                lang,
                bundle="roles",
            )
        except Exception:
            pass
        await bridge.send_text(
            int(uid_s),
            texts.get(
                "DetectiveSnoop",
                lang,
                label,
                bundle="results",
            ),
        )


async def step_princess(
    ctx: dict[str, Any],
    lang: str,
    *,
    keys: RedisKeySpace,
) -> None:
    """Princess prison after night > 2."""
    _ = lang
    night = int(ctx.get("night_no") or 0)
    if night <= 2:
        return
    roles = ctx.get("roles") or {}
    for uid_s, role_id in roles.items():
        if role_id != "role_Princess":
            continue
        raw = (ctx.get("actions") or {}).get(uid_s)
        if not raw:
            continue
        redis = await get_redis()
        await redis.hset(
            keys.game_flags(int(ctx["chat_id"])),
            keys.field("princess_prison"),
            str(raw),
        )
