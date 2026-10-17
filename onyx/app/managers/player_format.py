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
from app.managers.text_managers import TextManager


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
    tpl = texts.get(
        "phase_player_list",
        lang,
        len(living),
        "\0",
        bundle=bundle,
    )
    await bridge.send_text(
        chat_id,
        tpl.replace("\0", live_body, 1),
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
