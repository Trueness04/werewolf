"""Night death announce helpers."""

from __future__ import annotations

from typing import Any

from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.night_village import player
from app.managers.text_managers import TextManager
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


async def announce_night_results(
    chat_id: int,
    lang: str,
    ctx: dict[str, Any],
    *,
    bridge: ChatBridge,
    texts: TextManager,
) -> None:
    """Send night result messages to group + victims."""
    registry = _Registry()
    for msg in ctx["messages"]:
        text = texts.get(str(msg), lang, bundle="results")
        await bridge.send_text(chat_id, text)
    for entry in ctx.get("dm_messages") or []:
        if not entry:
            continue
        uid = int(entry[0])
        # Skip AI players (negative IDs are not real Telegram users)
        if uid < 0:
            continue
        key = str(entry[1])
        fmt_args: list[object] = []
        if len(entry) > 2:
            # optional target id → display name
            try:
                tid = int(entry[2])
            except (TypeError, ValueError):
                tid = None
            if tid is not None:
                prow = player(ctx, tid)
                fmt_args.append(
                    str(prow["fullname"]) if prow else str(tid)
                )
        await bridge.send_text(
            uid,
            texts.get(
                key,
                lang,
                *fmt_args,
                bundle="results",
            ),
        )
    if not ctx["deaths"]:
        text = texts.get(
            "NoAttakInDay",
            lang,
            bundle="results",
        )
        await bridge.send_text(chat_id, text)
        return
    death_pvs = ctx.get("death_pvs") or {}
    for uid in ctx["deaths"]:
        prow = player(ctx, int(uid))
        from app.managers.player_format import (
            mention_html,
        )

        raw_name = str(prow["fullname"]) if prow else str(uid)
        name = mention_html(int(uid), raw_name)
        role_id = str(prow.get("role")) if prow else ""
        role_name = ""
        if role_id:
            role_name = texts.get(
                str(
                    registry.definition(role_id)[
                        "message_keys"
                    ]["name"]
                ),
                lang,
                bundle="roles",
            )
        text = texts.get(
            "DefaultKilled",
            lang,
            name,
            role_name,
            bundle="results",
        )
        await bridge.send_text(chat_id, text)
        # Skip death PV for AI players (negative IDs)
        if int(uid) < 0:
            continue
        pv_key = death_pvs.get(int(uid)) or death_pvs.get(
            uid
        )
        if pv_key:
            await bridge.send_text(
                int(uid),
                texts.get(
                    str(pv_key),
                    lang,
                    bundle="results",
                ),
            )
        else:
            await bridge.send_text(
                int(uid),
                texts.get(
                    "you_died_night",
                    lang,
                    role_name or name,
                    bundle="results",
                ),
            )
