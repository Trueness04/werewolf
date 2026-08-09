"""Pick session senior (highest rank) and send PV panel."""

from __future__ import annotations

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from app.database.models.group import GroupRow
from app.database.models.user import UserRow
from app.database.session import session_scope
from app.keyboards.inline.senior_keyboard import (
    build_senior_keyboard,
)
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.lobby_manager import LobbyManager
from app.managers.text_managers import TextManager


async def pick_session_senior(
    chat_id: int,
    *,
    keys: RedisKeySpace | None = None,
    lobby: LobbyManager | None = None,
) -> int | None:
    """Highest rank among lobby; ties: xp, then user_id."""
    keys = keys or RedisKeySpace()
    lobby = lobby or LobbyManager()
    players = await lobby.list_players(chat_id)
    if not players:
        return None
    ids = [int(p["user_id"]) for p in players]
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(UserRow).where(
                    UserRow.user_id.in_(ids)
                )
            )
        ).scalars().all()
    by_id = {int(r.user_id): r for r in rows}

    def sort_key(uid: int) -> tuple[int, int, int]:
        row = by_id.get(uid)
        rank = int(row.rank) if row is not None else 1
        xp = int(row.xp) if row is not None else 0
        return (rank, xp, -uid)

    best = max(ids, key=sort_key)
    redis = await get_redis()
    await redis.hset(
        keys.game_flags(chat_id),
        keys.field("session_senior"),
        str(best),
    )
    return best


async def roles_locked(
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> bool:
    """True after leave join (roles assigned / running)."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    state = await redis.hget(
        keys.game_hash(chat_id),
        keys.field("game_state"),
    )
    if not state:
        return False
    return str(state) != "join"


async def read_panel_flags(
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> dict[str, bool]:
    """Session flags with group defaults."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    group = await _group_row(chat_id)

    async def flag(
        field: str,
        default: bool,
    ) -> bool:
        raw = await redis.hget(flags, keys.field(field))
        if raw is None:
            return default
        return str(raw) not in ("0", "false", "no", "")

    vamp_def = bool(
        getattr(group, "vampire_role_on", True)
        if group
        else True
    )
    blood_def = bool(
        getattr(group, "bloodthirsty_role_on", True)
        if group
        else True
    )
    mute_def = bool(
        getattr(group, "mute_die", False)
        if group
        else False
    )
    secret_def = bool(
        getattr(group, "secret_vote", False)
        if group
        else False
    )
    return {
        "magic_allowed": await flag(
            "magic_allowed",
            True,
        ),
        "mute_die": await flag("mute_die", mute_def),
        "secret_vote": await flag(
            "secret_vote",
            secret_def,
        ),
        "vampire_on": await flag(
            "vampire_role_on",
            vamp_def,
        ),
        "blood_on": await flag(
            "bloodthirsty_role_on",
            blood_def,
        ),
    }


async def send_senior_panel(
    chat_id: int,
    senior_id: int,
    *,
    bridge: ChatBridge,
    texts: TextManager | None = None,
    keys: RedisKeySpace | None = None,
    lang: str | None = None,
    force: bool = False,
) -> None:
    """DM «پنل کنترل بازی» once per senior (unless force)."""
    keys = keys or RedisKeySpace()
    texts = texts or TextManager()
    lang = lang or get_settings().default_lang
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    sent = await redis.hget(
        flags,
        keys.field("senior_panel_sent"),
    )
    if (
        not force
        and sent
        and str(sent) == str(senior_id)
    ):
        return
    panel = await read_panel_flags(chat_id, keys)
    locked = await roles_locked(chat_id, keys)
    markup = build_senior_keyboard(
        texts,
        lang,
        chat_id,
        magic_allowed=panel["magic_allowed"],
        mute_die=panel["mute_die"],
        secret_vote=panel["secret_vote"],
        vampire_on=panel["vampire_on"],
        blood_on=panel["blood_on"],
        roles_locked=locked,
    )
    title = texts.get(
        "SessionSeniorPanelTitle",
        lang,
        bundle="lobby",
    )
    body = texts.get(
        "SessionSeniorPanelBody",
        lang,
        bundle="lobby",
    )
    await bridge.send_text(
        senior_id,
        f"<b>{title}</b>\n\n{body}",
        reply_markup=markup,
    )
    await redis.hset(
        flags,
        keys.field("senior_panel_sent"),
        str(senior_id),
    )
    log_game_event(
        "session_senior_panel",
        chat_id=chat_id,
        user_id=senior_id,
    )


async def maybe_refresh_session_senior(
    chat_id: int,
    *,
    bridge: ChatBridge,
    texts: TextManager | None = None,
    keys: RedisKeySpace | None = None,
    lobby: LobbyManager | None = None,
    lang: str | None = None,
) -> int | None:
    """Recompute senior on lobby join updates; send panel."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    if await roles_locked(chat_id, keys):
        raw = await redis.hget(
            keys.game_flags(chat_id),
            keys.field("session_senior"),
        )
        return int(raw) if raw else None
    senior = await pick_session_senior(
        chat_id,
        keys=keys,
        lobby=lobby,
    )
    if senior is None:
        return None
    prev = await redis.hget(
        keys.game_flags(chat_id),
        keys.field("senior_panel_sent"),
    )
    force = prev is not None and str(prev) != str(senior)
    await send_senior_panel(
        chat_id,
        senior,
        bridge=bridge,
        texts=texts,
        keys=keys,
        lang=lang,
        force=force,
    )
    return senior


async def is_session_senior(
    chat_id: int,
    user_id: int,
    keys: RedisKeySpace | None = None,
) -> bool:
    """True if user_id matches SessionSenior flag."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    raw = await redis.hget(
        keys.game_flags(chat_id),
        keys.field("session_senior"),
    )
    if not raw:
        return False
    return int(raw) == int(user_id)


async def _group_row(chat_id: int) -> GroupRow | None:
    async with session_scope() as session:
        return (
            await session.execute(
                select(GroupRow).where(
                    GroupRow.chat_id == chat_id
                )
            )
        ).scalar_one_or_none()
