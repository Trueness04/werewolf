"""End-game win list (split of player_format_roster)."""

from __future__ import annotations

import json

from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import WIN_CODES
from app.managers.chat_bridge import ChatBridge
from app.managers.json_loader import load_json
from app.managers.player_format_roster import (
    NL,
    PLAYER_CUSTOM_EMOJI,
    RoleRegistry,
    _load_custom_emojis,
    _role_label,
    _roster_markdown,
    _texts,
    ltr,
)
from app.managers.text_managers import TextManager


async def send_win_list(
    bridge: ChatBridge,
    texts: TextManager,
    chat_id: int,
    lang: str,
    players: list[dict[str, Any]],
    winner: str,
) -> None:
    """End-game table: every seat, role revealed, win flag."""
    from app.managers.player_format import player_name
    from app.managers.win_census import WinCensus
    from app.managers.nix_medals import user_medal

    redis = await get_redis()
    keys = RedisKeySpace()
    await _load_custom_emojis(players)
    roles_map = json.loads(
        await redis.get(
            keys.game_roles(chat_id)
        )
        or "{}"
    )
    lover_uids: set[int] = set()
    if winner == "lover":
        from app.managers.village_links import (
            parse_lover_pair,
        )

        raw_pair = await redis.hget(
            keys.game_flags(chat_id),
            keys.field("lover_pair"),
        )
        parsed = parse_lover_pair(raw_pair)
        if parsed:
            lover_uids = {parsed[0], parsed[1]}
    registry = RoleRegistry()
    census = WinCensus()
    codes = load_json(WIN_CODES)
    rows = []
    for item in players:
        uid = int(item["user_id"])
        rid = str(roles_map.get(str(uid), "") or "")
        role_cell = (
            _role_label(
                texts,
                lang,
                rid,
                registry,
            )
            if rid
            else ""
        )
        medal, _label = await user_medal(uid)
        custom = PLAYER_CUSTOM_EMOJI.get(uid, "")
        alive = bool(item.get("alive", True))
        neutral = bool(item.get("neutral", False))
        if neutral:
            status = (
                chr(0x1F3C3)
                if item.get("fugitive")
                else chr(0x1F634)
            )
        else:
            status = (
                chr(0x1F642) if alive else chr(0x1FAA6)
            )
        won = bool(alive) and bool(rid) and (
            census.bucket(rid) == winner
            or uid in lover_uids
        )
        win_cell = (
            chr(0x1F947) if won else chr(0x26AB)
        )
        rows.append(
            (
                custom,
                f"{player_name(item)}.[{medal}]",
                win_cell,
                status,
                role_cell,
            )
        )
    head = _texts.get(
        "roster_count",
        "fa",
        sum(
            1
            for p in players
            if p.get("alive", True)
        ),
        len(players),
        bundle="webapp",
    ) + NL + texts.get(
        str(
            codes["caption_keys"].get(
                winner, "winner_nothing"
            )
        ),
        lang,
        bundle=str(codes["bundle"]),
    )
    md = _roster_markdown(head, rows, "win_table_head")
    if not await bridge.send_rich(chat_id, md):
        for _c, nm, w, s, r in rows:
            line = f"{w}.{nm}.{s}.{r}".rstrip()
            await bridge.send_text(chat_id, ltr(line))
