"""Night death announce helpers."""

from __future__ import annotations

from typing import Any

from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.night_village import player
from app.managers.text_managers import TextManager
from importlib import import_module

_Registry = import_module("app.class.roles.registry").RoleRegistry


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
        if uid < 0:
            continue
        key = str(entry[1])
        fmt_args: list[object] = []
        if len(entry) > 2:
            try:
                tid = int(entry[2])
            except (TypeError, ValueError):
                tid = None
            if tid is not None:
                prow = player(ctx, tid)
                fmt_args.append(str(prow["fullname"]) if prow else str(tid))
        await bridge.send_text(
            uid,
            texts.get(key, lang, *fmt_args, bundle="results"),
        )
    if not ctx["deaths"]:
        text = texts.get("NoAttakInDay", lang, bundle="results")
        await bridge.send_text(chat_id, text)
        return
    death_pvs = ctx.get("death_pvs") or {}
    for uid in ctx["deaths"]:
        prow = player(ctx, int(uid))
        from app.managers.player_format import mention_html

        raw_name = str(prow["fullname"]) if prow else str(uid)
        name = mention_html(int(uid), raw_name)
        role_id = str(prow.get("role")) if prow else ""
        role_name = ""
        if role_id:
            defn = registry.definition(role_id)
            msg_keys = defn.get("message_keys", {})
            role_name = texts.get(
                str(msg_keys.get("name", "")),
                lang,
                bundle="roles",
            )
        cause = (ctx.get("death_cause") or {}).get(int(uid))
        if cause == "wolf":
            text = texts.get(
                "WolfKilled",
                lang,
                name,
                role_name,
                bundle="results",
            )
        elif cause == "lover":
            from app.managers.game_event import log_to_group

            partner_id = (ctx.get("lover_cause") or {}).get(int(uid))
            await log_to_group(
                bridge,
                f"[NIGHT] lover {uid}<-{partner_id}"
                f" pair={ctx.get('lover_pair')}",
            )
            partner_name = name
            if partner_id is not None:
                prow2 = player(ctx, int(partner_id))
                raw2 = str(prow2["fullname"]) if prow2 else str(partner_id)
                partner_name = mention_html(int(partner_id), raw2)
            short = texts.get("LoverDied", lang, bundle="results")
            if "{0}" not in short:
                text = texts.get(
                    "LoverDied",
                    lang,
                    partner_name,
                    name,
                    role_name,
                    bundle="general",
                )
            else:
                text = texts.get(
                    "LoverDied",
                    lang,
                    partner_name,
                    name,
                    role_name,
                    bundle="results",
                )
        else:
            text = texts.get(
                "DefaultKilled",
                lang,
                name,
                role_name,
                bundle="results",
            )
        await bridge.send_text(chat_id, text)
        if int(uid) < 0:
            continue
        pv_key = death_pvs.get(int(uid)) or death_pvs.get(uid)
        if pv_key:
            await bridge.send_text(
                int(uid),
                texts.get(str(pv_key), lang, bundle="results"),
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
