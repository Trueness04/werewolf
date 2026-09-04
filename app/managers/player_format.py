"""Player mention + living roster helpers."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import URL_TEMPLATES
from app.database.models.player import PlayerRow
from app.database.session import session_scope
from app.managers.chat_bridge import ChatBridge
from app.managers.json_loader import load_json
from importlib import import_module

from app.managers.text_managers import TextManager

# ponytail: "app.class" contains the `class` keyword — normal import
# syntax is illegal; project-wide convention is string import_module.
RoleRegistry = import_module(
    "app.class.roles.registry"
).RoleRegistry


def player_name(item: dict[str, Any]) -> str:
    """Best display name from a player dict."""
    for key in ("name", "fullname", "full_name"):
        raw = item.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return str(item.get("user_id", "?"))


def mention_html(user_id: int, name: str) -> str:
    """Telegram HTML label; real users get mentions."""
    safe = (
        str(name)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    if not safe:
        safe = str(user_id)
    # AI / fake seats cannot be deep-linked.
    if int(user_id) <= 0:
        return f"<b>{safe}</b>"
    tpl = str(load_json(URL_TEMPLATES)["user_mention_html"])
    return tpl.format(user_id=int(user_id), name=safe)


def mention_lines(
    players: list[dict[str, Any]],
    *,
    alive: bool | None = True,
) -> list[str]:
    """Build mention lines; alive=None keeps all."""
    lines: list[str] = []
    for item in players:
        is_alive = bool(item.get("alive", True))
        if alive is True and not is_alive:
            continue
        if alive is False and is_alive:
            continue
        uid = int(item["user_id"])
        lines.append(mention_html(uid, player_name(item)))
    return lines


async def _names_from_db(
    chat_id: int,
    keys: RedisKeySpace,
) -> dict[int, str]:
    """Map user_id -> fullname from PostgreSQL."""
    redis = await get_redis()
    game_id = int(
        await redis.hget(
            keys.game_hash(chat_id),
            keys.field("game_id"),
        )
        or "0"
    )
    if game_id <= 0:
        return {}
    out: dict[int, str] = {}
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(PlayerRow).where(
                    PlayerRow.game_id == game_id
                )
            )
        ).scalars().all()
        for row in rows:
            if row.fullname:
                out[int(row.user_id)] = str(row.fullname)
    return out


async def load_game_players(
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> list[dict[str, Any]]:
    """Load players JSON and refresh alive + names."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    raw = await redis.get(keys.game_players(chat_id))
    if not raw:
        return []
    try:
        players = json.loads(raw)
    except json.JSONDecodeError:
        return []
    db_names = await _names_from_db(chat_id, keys)
    out: list[dict[str, Any]] = []
    for item in players:
        uid = int(item["user_id"])
        state = await redis.get(keys.player_state(uid))
        row = dict(item)
        if not player_name(row) or player_name(row) == str(
            uid
        ):
            if uid in db_names:
                row["name"] = db_names[uid]
        elif "name" not in row:
            row["name"] = player_name(row)
        row["alive"] = state != "dead"
        out.append(row)
    return out


def _cell(name: str) -> str:
    """One-line markdown table cell; pipes neutralized."""
    return (
        str(name)
        .replace("\n", " ")
        .replace("|", "/")
    )


# ponytail: custom-emoji slot — fill role_id -> icon_custom_emoji_id
# once IDs are obtained (needs premium); rich-markdown tables cannot
# embed custom-emoji IDs, so this stays a wiring hook for now.
ROLE_CUSTOM_EMOJI: dict[str, str] = {}


def _role_label(
    texts: TextManager,
    lang: str,
    role_id: str,
    registry: RoleRegistry,
) -> str:
    """Localized role display name (emoji built in) for roster."""
    _ = ROLE_CUSTOM_EMOJI.get(role_id, "")
    try:
        key = str(
            registry.definition(role_id)
            .get("message_keys", {})
            .get("name", "")
        )
    except KeyError:
        return role_id
    label = texts.get(key, lang, bundle="roles") if key else ""
    if not label or label == key:
        return role_id
    return label


def _roster_markdown(
    head: str,
    rows: list[tuple[str, str, str]],
    player_col: str,
    role_col: str,
) -> str:
    """One Rich-Markdown table: all seats, role shown when dead."""
    if not rows:
        return f"**{head}**\n\n-"
    body = "\n".join(
        f"| {num} | {_cell(name)} | {_cell(role)} |"
        for num, name, role in rows
    )
    table = (
        f"| # | {player_col} | {role_col} |\n"
        f"|:-:|------|------|\n"
        f"{body}"
    )
    return f"**{head}**\n\n{table}"


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
    if players is None:
        players = await load_game_players(chat_id)
    living = mention_lines(players, alive=True)
    dead = mention_lines(players, alive=False)
    live_body = "\n".join(
        f"{i}. {n}" for i, n in enumerate(living, 1)
    ) or "-"
    live_tpl = texts.get(
        "phase_player_list",
        lang,
        len(living),
        "\0",
        bundle=bundle,
    )
    # Rich path: one markdown table, all seats, role revealed when dead.
    redis = await get_redis()
    roles_map = json.loads(
        await redis.get(
            RedisKeySpace().game_roles(chat_id)
        )
        or "{}"
    )
    registry = RoleRegistry()
    rows: list[tuple[str, str, str]] = []
    for i, item in enumerate(players, 1):
        role_cell = ""
        if not bool(item.get("alive", True)):
            rid = str(
                roles_map.get(str(item["user_id"]), "")
            )
            if rid:
                role_cell = _role_label(
                    texts, lang, rid, registry,
                )
        rows.append((str(i), player_name(item), role_cell))
    rich_md = _roster_markdown(
        head=texts.get(
            "roster_title",
            lang,
            len(players),
            bundle=bundle,
        ),
        rows=rows,
        player_col=texts.get("player_col", lang, bundle=bundle),
        role_col=texts.get("col_role", lang, bundle=bundle),
    )
    if await bridge.send_rich(chat_id, rich_md):
        return
    # Fallback: legacy two plain messages.
    await bridge.send_text(
        chat_id,
        live_tpl.replace("\0", live_body, 1),
    )
    if dead:
        dead_body = "\n".join(
            f"{i}. {n}" for i, n in enumerate(dead, 1)
        )
        tpl_d = texts.get(
            "phase_dead_list",
            lang,
            len(dead),
            "\0",
            bundle=bundle,
        )
        await bridge.send_text(
            chat_id,
            tpl_d.replace("\0", dead_body, 1),
        )
