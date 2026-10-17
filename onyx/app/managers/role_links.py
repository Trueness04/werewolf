"""RoleLink registry — death sync hooks between roles."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.player_snapshot import load_enriched_players
from app.managers.text_managers import TextManager

EffectFn = Callable[..., Awaitable[None]]

LINKS: list[dict[str, str]] = [
    {
        "when": "death",
        "source_role": "role_BlackKnight",
        "effect": "refresh_prince_save",
    },
    {
        "when": "death",
        "source_role": "role_Khenyager",
        "effect": "kenyager_death_love",
    },
    {
        "when": "death",
        "source_role": "role_Sweetheart",
        "effect": "sweetheart_death_chaos",
    },
]


async def refresh_prince_save(
    chat_id: int,
    dead_id: int,
    *,
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
    keys: RedisKeySpace,
) -> None:
    """PN-03: BlackKnight death refreshes prince lynch save."""
    players = await load_enriched_players(keys, chat_id)
    prince = next(
        (
            p
            for p in players
            if p.get("role") == "role_Shahzade"
            and p.get("alive", True)
        ),
        None,
    )
    if prince is None:
        return
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    await redis.hdel(
        flags,
        keys.field("prince_saved"),
    )
    prince_id = int(prince["user_id"])
    await bridge.send_text(
        prince_id,
        texts.get(
            "CrownHeirPrince",
            lang,
            bundle="lobby",
        ),
    )
    await bridge.send_text(
        dead_id,
        texts.get(
            "CrownHeirBlackKnight",
            lang,
            bundle="lobby",
        ),
    )
    log_game_event(
        "role_link_prince_heir",
        chat_id=chat_id,
        user_id=dead_id,
        prince_id=prince_id,
    )


async def kenyager_death_love(
    chat_id: int,
    dead_id: int,
    *,
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
    keys: RedisKeySpace,
) -> None:
    """PN-04: Khenyager death marks sweetheart love team."""
    _ = dead_id
    players = await load_enriched_players(keys, chat_id)
    sweet = next(
        (
            p
            for p in players
            if p.get("role") == "role_Sweetheart"
            and p.get("alive", True)
        ),
        None,
    )
    if sweet is None:
        return
    redis = await get_redis()
    await redis.hset(
        keys.game_flags(chat_id),
        keys.field("sweetheart_love_team"),
        "khenyager",
    )
    await bridge.send_text(
        int(sweet["user_id"]),
        texts.get(
            "DelbarKenyagerLink",
            lang,
            bundle="lobby",
        ),
    )
    log_game_event(
        "role_link_kenyager_love",
        chat_id=chat_id,
        sweetheart_id=int(sweet["user_id"]),
    )


async def sweetheart_death_chaos(
    chat_id: int,
    dead_id: int,
    *,
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
    keys: RedisKeySpace,
) -> None:
    """PN-04: Sweetheart death → trouble (chaos vote)."""
    _ = dead_id
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    await redis.hset(
        flags,
        mapping={
            keys.field("trouble"): "1",
            keys.field("not_send_day"): "1",
        },
    )
    await bridge.send_text(
        chat_id,
        texts.get(
            "SweetheartChaos",
            lang,
            bundle="lobby",
        ),
    )
    log_game_event(
        "role_link_sweetheart_chaos",
        chat_id=chat_id,
    )


_EFFECTS: dict[str, EffectFn] = {
    "refresh_prince_save": refresh_prince_save,
    "kenyager_death_love": kenyager_death_love,
    "sweetheart_death_chaos": sweetheart_death_chaos,
}


async def process_death_links(
    chat_id: int,
    user_id: int,
    role_id: str | None,
    *,
    bridge: ChatBridge | None = None,
    texts: TextManager | None = None,
    keys: RedisKeySpace | None = None,
    lang: str | None = None,
) -> None:
    """Run LINKS where when=death and source_role matches."""
    if not role_id:
        return
    keys = keys or RedisKeySpace()
    texts = texts or TextManager()
    lang = lang or get_settings().default_lang
    if bridge is None:
        return
    for link in LINKS:
        if link.get("when") != "death":
            continue
        if link.get("source_role") != role_id:
            continue
        effect_name = link.get("effect") or ""
        fn = _EFFECTS.get(effect_name)
        if fn is None:
            continue
        await fn(
            chat_id,
            user_id,
            bridge=bridge,
            texts=texts,
            lang=lang,
            keys=keys,
        )


async def on_kenyager_night_success(
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> None:
    """PN-04: bard night success → sweetheart_love_team."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    await redis.hset(
        keys.game_flags(chat_id),
        keys.field("sweetheart_love_team"),
        "khenyager",
    )
