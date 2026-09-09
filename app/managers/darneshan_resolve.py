"""DarNeshan mark → lynch pick → cult convert (PN-09)."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import ROOT
from app.managers.chat_bridge import ChatBridge
from app.managers.convert_player import convert_player
from app.managers.cult_helpers import cult_rules
from app.managers.json_loader import load_json
from app.managers.logger_manager import get_logger
from app.managers.night_village import player
from app.managers.text_managers import TextManager
from app.managers.darneshan_pick import (  # noqa: F401
    apply_darneshan_pick,
    maybe_open_darneshan_pick,
)

_CHANCES = ROOT / "data" / "config" / "field_chances.json"


def cult_mongo_roles() -> set[str]:
    """Roles on ferqeTeem mongo roster (incl. DarNeshan)."""
    return {str(r) for r in cult_rules()["mongo_team"]}


async def resolve_dar_neshan_mark(
    ctx: dict[str, Any],
) -> None:
    """Night resolve: set gallows mark (non-visit)."""
    if ctx.get("blood_moon_active"):
        return
    for item in ctx["players"]:
        if item.get("role") != "role_DarNeshan":
            continue
        if not item.get("alive", True):
            continue
        marker_id = int(item["user_id"])
        if marker_id in ctx["deaths"]:
            continue
        raw = ctx["actions"].get(str(marker_id))
        if not raw:
            ctx.setdefault("dm_messages", []).append(
                (marker_id, "DarNeshanSkipMark")
            )
            continue
        try:
            tid = int(raw)
        except ValueError as exc:
            get_logger().warning("silent_swallow.line=52.exc={}", exc)
            continue
        target = player(ctx, tid)
        if target is None or not target.get("alive", True):
            continue
        if tid == marker_id:
            continue
        trole = str(target.get("role") or "")
        if trole in cult_mongo_roles():
            continue
        if trole == "role_BrideTheDead":
            continue
        ctx["flags_out"]["darneshan_mark_target"] = str(tid)
        ctx["flags_out"]["darneshan_mark_by"] = str(
            marker_id
        )
        ctx["flags_out"]["darneshan_mark_night"] = str(
            ctx.get("night_no") or 0
        )
        ctx.setdefault("dm_messages", []).append(
            (marker_id, "DarNeshanMarkSet", tid)
        )


def clear_mark_flags(flags_out: dict[str, Any]) -> None:
    """Wipe active mark keys (empty string = delete)."""
    flags_out["darneshan_mark_target"] = ""
    flags_out["darneshan_mark_by"] = ""
    flags_out["darneshan_mark_night"] = ""


def burn_mark_if_target_dead(ctx: dict[str, Any]) -> None:
    """Night death of mark target burns without convert."""
    mark = (
        ctx.get("darneshan_mark_target")
        or (ctx.get("flags") or {}).get(
            "darneshan_mark_target"
        )
        or ctx["flags_out"].get("darneshan_mark_target")
    )
    if not mark:
        return
    try:
        tid = int(mark)
    except (TypeError, ValueError) as exc:
        get_logger().warning("silent_swallow.line=96.exc={}", exc)
        return
    if tid not in ctx["deaths"]:
        return
    marker = (
        ctx.get("darneshan_mark_by")
        or (ctx.get("flags") or {}).get("darneshan_mark_by")
    )
    clear_mark_flags(ctx["flags_out"])
    if marker:
        try:
            mid = int(marker)
        except (TypeError, ValueError) as exc:
            get_logger().warning("silent_swallow.line=108.exc={}", exc)
            return
        ctx.setdefault("dm_messages", []).append(
            (mid, "DarNeshanMarkTargetDead", tid)
        )


from app.managers.darneshan_pick import (  # noqa: F401
    apply_darneshan_pick,
    maybe_open_darneshan_pick,
)


async def timeout_darneshan_pick(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    lang: str,
    chat_id: int,
    actor_id: int,
    to_night,
) -> None:
    """Pick window expired without convert."""
    await bridge.send_text(
        actor_id,
        texts.get(
            "DarNeshanPickTimeout",
            lang,
            bundle="vote",
        ),
    )
    redis = await get_redis()
    await _clear_mark_redis(redis, keys, chat_id)
    await redis.hdel(
        keys.game_flags(chat_id),
        keys.field("darneshan_pick_pending"),
    )
    await to_night(chat_id)


async def burn_mark_after_failed_lynch(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    chat_id: int,
    lang: str,
) -> None:
    """Vote ended without killing mark target."""
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
        return
    players = json.loads(
        await redis.get(keys.game_players(chat_id)) or "[]"
    )
    name = str(mark)
    for item in players:
        if int(item["user_id"]) == int(mark):
            name = str(item["fullname"])
            break
    await bridge.send_text(
        int(marker),
        texts.get(
            "DarNeshanMarkBurned",
            lang,
            name,
            bundle="vote",
        ),
    )
    await _clear_mark_redis(redis, keys, chat_id)


async def _clear_mark_redis(
    redis: Any,
    keys: RedisKeySpace,
    chat_id: int,
) -> None:
    """Delete mark fields from game flags."""
    flags = keys.game_flags(chat_id)
    await redis.hdel(
        flags,
        keys.field("darneshan_mark_target"),
        keys.field("darneshan_mark_by"),
        keys.field("darneshan_mark_night"),
        keys.field("darneshan_pick_pending"),
    )
