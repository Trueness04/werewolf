"""Join flow (PHP joinToGAME_ 12 steps)."""

from __future__ import annotations

from time import time

from telegram import Update
from telegram.ext import ContextTypes

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import COMMANDS_JSON, GAME_PHASES
from app.handlers import deps
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import GroupInactive
from app.managers.json_loader import load_json


async def start_payload_join(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start joinToGAME_<chat_id> in PV."""
    user = update.effective_user
    if user is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    if not context.args:
        await context.bot.send_message(
            chat_id=user.id,
            text=tm.get("GameStartOnGroup", lang),
        )
        return
    payload = context.args[0]
    cmds = load_json(COMMANDS_JSON)
    prefix = str(cmds["start_payload_prefix"])
    if not payload.startswith(prefix):
        await context.bot.send_message(
            chat_id=user.id,
            text=tm.get("GameStartOnGroup", lang),
        )
        return
    raw_chat = payload[len(prefix) :]
    try:
        chat_id = int(raw_chat)
    except ValueError:
        return
    await run_join_steps(update, context, chat_id)


async def run_join_steps(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> None:
    """Execute the 12 validation steps in order."""
    user = update.effective_user
    if user is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    cfg = deps.settings()
    # 1 ban
    if await deps.ban_block(
        update,
        user.id,
        lang,
        context,
    ):
        log_game_event(
            "join_fail_ban",
            chat_id=chat_id,
            user_id=user.id,
        )
        return
    bridge = deps.bridge(context)
    # 2 membership allow
    try:
        status = await bridge.get_member_status(
            chat_id,
            user.id,
        )
    except Exception:
        status = "left"
    allow = 0 if status in {"left", "kicked"} else 1
    keys = RedisKeySpace()
    redis = await get_redis()
    # 3 already in another game
    other = await redis.get(keys.join_user(user.id))
    if other and int(other) != chat_id:
        await context.bot.send_message(
            chat_id=user.id,
            text=tm.get("YouInGame", lang),
        )
        log_game_event(
            "join_fail_other_game",
            chat_id=chat_id,
            user_id=user.id,
        )
        return
    # 4 allow
    if allow <= 0:
        await context.bot.send_message(
            chat_id=user.id,
            text=tm.get("NotAllowToJoin", lang),
        )
        log_game_event(
            "join_fail_allow",
            chat_id=chat_id,
            user_id=user.id,
        )
        return
    lobby = deps.lobby_mgr()
    fullname = user.full_name
    # 5 duplicate name
    if await lobby.name_taken(chat_id, fullname):
        await context.bot.send_message(
            chat_id=user.id,
            text=tm.get("NotNameAllow", lang, fullname),
        )
        log_game_event(
            "join_fail_name",
            chat_id=chat_id,
            user_id=user.id,
        )
        return
    # 6 capacity
    count = await lobby.count_players(chat_id)
    group = await deps.state_mgr().ensure_group_active(
        chat_id,
    )
    from app.managers.group_limits import max_players_of

    cap = max_players_of(group, cfg) if group else (
        cfg.max_players
    )
    if count >= cap:
        await context.bot.send_message(
            chat_id=user.id,
            text=tm.get(
                "MaxPlayer",
                lang,
                cap,
            ),
        )
        log_game_event(
            "join_fail_max",
            chat_id=chat_id,
            user_id=user.id,
        )
        return
    # 7 valid game
    key = keys.game_hash(chat_id)
    exists = await redis.exists(key)
    if not exists:
        await context.bot.send_message(
            chat_id=user.id,
            text=tm.get("NotFoundGameId", lang),
        )
        log_game_event(
            "join_fail_missing",
            chat_id=chat_id,
            user_id=user.id,
        )
        return
    # 8 time/state silent
    phases = load_json(GAME_PHASES)
    join_name = str(phases["redis_phases"]["join"])
    data = await redis.hgetall(key)
    state = data.get(keys.field("game_state"), "")
    timer = int(data.get(keys.field("timer"), "0"))
    left = timer - int(time())
    if left <= 0 or state != join_name:
        return
    # 9 lock
    lock = keys.player_join_lock(user.id)
    locked = await redis.set(
        lock,
        "1",
        nx=True,
        ex=15,
    )
    if not locked:
        return
    mode = str(data.get(keys.field("game_mode"), ""))
    # 10 coin mode
    # 11 register
    await lobby.register_player(
        chat_id,
        user.id,
        fullname,
    )
    from app.managers.lobby_extend import bump_if_late_join

    await bump_if_late_join(lobby, chat_id, cfg)
    # 12 confirm PV
    try:
        title = await bridge.get_chat_title(chat_id)
    except Exception:
        title = str(chat_id)
    await context.bot.send_message(
        chat_id=user.id,
        text=tm.get("JoinTheGame", lang, title),
    )
    log_game_event(
        "join_ok",
        chat_id=chat_id,
        user_id=user.id,
    )


async def join_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Group /join redirects user to deeplink hint."""
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    state_manager = deps.state_mgr()
    try:
        await state_manager.get_group_state(chat.id)
    except GroupInactive:
        return
    url = deps.join_url(chat.id)
    await context.bot.send_message(
        chat_id=user.id,
        text=url,
    )
    _ = tm
