"""Roster formatting helpers (split of player_format)."""

from __future__ import annotations

import json

from typing import Any

from app.managers.text_managers import TextManager

_texts = TextManager()
NL = chr(10)
ROW_FMT = chr(124).join(
    chr(32) + "{" + str(i) + "}" + chr(32)
    for i in range(5)
)

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from importlib import import_module
from app.managers.logger_manager import get_logger

RoleRegistry = import_module(
    "app.class.roles.registry"
).RoleRegistry

def _cell(name: str) -> str:
    """One-line markdown table cell; pipes neutralized."""
    return (
        str(name)
        .replace(NL, ".")
        .replace("|", "/")
    )

def ltr(text: str) -> str:
    """Full LTR isolate (LRI…PDI) for FA/EN text."""
    value = str(text or "")
    return chr(0x2066) + value + chr(0x2069)

PLAYER_CUSTOM_EMOJI: dict[int, str] = {}
ROLE_CUSTOM_EMOJI: dict[str, str] = {}

async def _load_custom_emojis(
    players: list[dict[str, Any]],
) -> None:
    """Fill PLAYER_CUSTOM_EMOJI from Redis user prefs."""
    redis = await get_redis()
    keys = RedisKeySpace()
    for item in players:
        uid = int(item["user_id"])
        key = keys.user_custom_emoji(uid)
        if not key:
            continue
        val = await redis.get(key)
        PLAYER_CUSTOM_EMOJI[uid] = (
            str(val) if val else ""
        )

async def set_user_custom_emoji(
    user_id: int,
    emoji: str,
) -> bool:
    """Persist one user's custom emoji (picker calls this).

    Reserved emoji (roles, medals, 🥇⚫️🙂☠️) are refused.
    """
    from app.managers.nix_medals import (
        is_reserved_emoji,
    )

    if emoji and is_reserved_emoji(emoji):
        return False
    redis = await get_redis()
    key = RedisKeySpace().user_custom_emoji(
        user_id
    )
    if not key:
        return False
    await redis.set(key, emoji)
    PLAYER_CUSTOM_EMOJI[user_id] = emoji
    return True

def _role_label(
    texts: TextManager,
    lang: str,
    role_id: str,
    registry: RoleRegistry,
) -> str:
    """Localized role display name (emoji built in) for roster."""
    _ = ROLE_CUSTOM_EMOJI.get(role_id, "")
    try:
        key = str(registry.definition(
            role_id
        ).get("message_keys", {}).get(
            "name", ""
        ))
    except KeyError as exc:
        get_logger().warning("silent_swallow.line=99.exc={}", exc)
        return role_id
    label = (
        texts.get(key, lang, bundle="roles")
        if key else ""
    )
    return role_id if (
        not label or label == key
    ) else label

def _roster_markdown(
    head: str,
    rows: list,
    head_key: str = "roster_table_head",
) -> str:
    """Rich-Markdown LTR table; data-sourced titles.
    Row: (custom, name, win, status, role)."""
    if not rows:
        return head
    titles = _texts.get(
        head_key,
        "fa",
        bundle="webapp",
    )
    table = titles + NL.join(
        ROW_FMT.format(
            _cell(c),
            _cell(ltr(n)),
            _cell(w),
            _cell(s),
            _cell(ltr(r)) if r else "",
        )
        for c, n, w, s, r in rows
    )
    return _texts.get(
            "roster_head_join",
            "fa",
            head,
            table,
            bundle="webapp",
        )

async def announce_roster(
    bridge: ChatBridge,
    texts: TextManager,
    chat_id: int,
    lang: str,
    players: list[dict[str, Any]] | None = None,
    *,
    bundle: str = "lobby",
) -> None:
    """Send living (+ dead) roster to the group."""
    from app.managers.player_format import (
        load_game_players,
        mention_lines,
        player_name,
    )

    if players is None:
        players = await load_game_players(chat_id)
    await _load_custom_emojis(players)
    living = mention_lines(
        players,
        alive=True,
    )
    dead = mention_lines(
        players,
        alive=False,
    )
    live_body = NL.join(
        f"{i}.{n}"
        for i, n in enumerate(living, 1)
    ) or "-"
    live_tpl = texts.get(
        "phase_player_list",
        lang,
        len(living),
        "\x00",
        bundle=bundle,
    )
    redis = await get_redis()
    roles_map = json.loads(
        await redis.get(
            RedisKeySpace().game_roles(chat_id)
        )
        or "{}"
    )
    registry = RoleRegistry()
    rows = []
    from app.managers.nix_medals import (
        user_medal,
    )

    for item in players:
        uid = int(item["user_id"])
        alive = bool(item.get("alive", True))
        rid = (
            str(roles_map.get(str(uid), ""))
            or ""
        )
        role_cell = ""
        if not alive and rid:
            role_cell = _role_label(
                texts,
                lang,
                rid,
                registry,
            )
        medal, _label = await user_medal(uid)
        custom = PLAYER_CUSTOM_EMOJI.get(uid, "")
        status = _texts.get(
            "roster_alive" if alive else "roster_dead",
            "fa",
            bundle="webapp",
        )
        rows.append(
            (
                custom,
                f"{player_name(item)}.[{medal}]",
                "",
                status,
                role_cell,
            )
        )
    try:
        rich_md = _roster_markdown(
            _texts.get(
                "roster_count",
                "fa",
                sum(
                    1
                    for p in players
                    if p.get("alive", True)
                ),
                len(players),
                bundle="webapp",
            ),
            rows,
        )
    except Exception:
        import logging
        import traceback

        logging.getLogger(__name__).exception(
            "roster.markdown.failed.c=%s",
            chat_id,
        )
        try:
            from app.managers.game_event import (
                log_to_group,
            )

            await log_to_group(
                bridge,
                f"roster.build.failed.c={chat_id}"
                "",
            )
        except Exception as exc:
            get_logger().warning("silent_swallow.line=323.exc={}", exc)
            pass
        rich_md = None
    if rich_md and await bridge.send_rich(
        chat_id, rich_md
    ):
        return
    await bridge.send_text(
        chat_id,
        live_tpl.replace("\x00", live_body, 1),
    )
    if not dead:
        return
    dead_body = NL.join(
        f"{i}.{n}"
        for i, n in enumerate(dead, 1)
    )
    tpl_d = texts.get(
        "phase_dead_list",
        lang,
        len(dead),
        "\x00",
        bundle=bundle,
    )
    await bridge.send_text(
        chat_id,
        tpl_d.replace("\x00", dead_body, 1),
    )
