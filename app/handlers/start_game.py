"""Start game handlers (PHP CM_StartGame)."""

from __future__ import annotations

import json
from time import time

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import URL_TEMPLATES
from app.filters import game_filters
from app.handlers import deps
from app.keyboards.inline.lobby_keyboard import (
    build_join_keyboard,
)
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameState,
    GroupInactive,
)
from app.managers.json_loader import load_json
from app.managers.logger_manager import get_logger
from app.managers.role_setup_manager import (
    RoleSetupManager,
)


async def start_game_entry(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Dispatch /start* commands to lobby start."""
    if update.effective_user is None:
        return
    if update.effective_chat is None:
        return
    if not update.message or not update.message.text:
        return
    command = update.message.text.split()[0]
    command = command.lstrip("/").split("@")[0]
    mode = deps.mode_for_command(command)
    await handle_start_game(update, context, mode)


async def handle_start_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: str,
) -> None:
    """Exact CM_StartGame ordered steps."""
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return
    log = get_logger()
    state_manager = deps.state_mgr()
    try:
        state = await state_manager.get_group_state(
            chat.id,
        )
    except GroupInactive:
        log.debug(
            "sg_skip"
            " chat={c} reason=inactive",
            chat.id,
        )
        return
    group = await state_manager.ensure_group_active(
        chat.id,
    )
    if group is None:
        log.debug(
            "sg_skip"
            " chat={c} reason=no_group",
            chat.id,
        )
        return
    lang = deps.group_lang(group)
    tm = deps.texts()
    if getattr(group, "sponsor_lock", False):
        from app.managers.sudo import is_sudo
        from app.database.models.admin import SponsorRow
        from app.database.session import session_scope
        from sqlalchemy import select

        allowed = is_sudo(user.id)
        if not allowed:
            async with session_scope() as session:
                sp = (
                    await session.execute(
                        select(SponsorRow).where(
                            SponsorRow.user_id == user.id,
                            SponsorRow.active.is_(True),
                        )
                    )
                ).scalar_one_or_none()
                allowed = sp is not None
        if not allowed:
            await context.bot.send_message(
                chat_id=chat.id,
                text=tm.get(
                    "SponsorLockBlocked",
                    lang,
                    bundle="lobby",
                ),
            )
            return
    if await deps.ban_block(
        update,
        user.id,
        lang,
        context,
    ):
        return
    if await game_filters.is_private(update):
        await context.bot.send_message(
            chat_id=user.id,
            text=tm.get("GameStartOnGroup", lang),
        )
        return
    if state == GameState.RUNNING:
        log.debug(
            "sg_skip"
            " chat={c} reason=running",
            chat.id,
        )
        return
    if state == GameState.JOINING:
        log.debug(
            "sg_skip"
            " chat={c} reason=joining",
            chat.id,
        )
        await _remind_join(update, context, lang, False)
        return
    if state == GameState.CHALLENGE_JOINING:
        log.debug(
            "sg_skip"
            " chat={c} reason=challenge",
            chat.id,
        )
        await _remind_join(update, context, lang, True)
        return
    log.debug(
        "sg_new c={}",
        c=chat.id,
    )
    await _start_new(
        update,
        context,
        mode,
        lang,
        group,
    )


async def _remind_join(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lang: str,
    challenge: bool,
) -> None:
    """Resend join button for existing lobby."""
    chat = update.effective_chat
    if chat is None:
        return
    tm = deps.texts()
    url = deps.join_url(chat.id)
    keyboard = build_join_keyboard(
        tm,
        lang,
        url,
        challenge=challenge,
    )
    key_name = (
        "StartLastChallenge"
        if challenge
        else "startLastGame"
    )
    mid = await context.bot.send_message(
        chat_id=chat.id,
        text=tm.get(key_name, lang),
        reply_markup=keyboard,
    )
    await _track_delete(chat.id, mid.message_id)


async def _start_new(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: str,
    lang: str,
    group,
) -> None:
    """NO_GAME branch: create lobby and announce."""
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return
    tm = deps.texts()
    roles = RoleSetupManager()
    if not await roles.is_setup_done(chat.id):
        await roles.unlock_all_roles(chat.id)
    info = deps.get_mode(mode)
    if info.needs_vampire_roles:
        from app.managers.role_pairs import (
            sync_role_toggles,
        )

        synced = sync_role_toggles(
            {
                "vampire": bool(group.vampire_role_on),
                "bloodthirsty": bool(
                    group.bloodthirsty_role_on
                ),
                "kalantar": True,
            }
        )
        if not (
            synced.get("vampire")
            and synced.get("bloodthirsty")
        ):
            await context.bot.send_message(
                chat_id=chat.id,
                text=tm.get("DisabledVampireMode", lang),
            )
            return
    fullname = user.full_name
    lobby = deps.lobby_mgr()
    game_id = await lobby.start_game_for_group(
        chat.id,
        mode,
        user.id,
        fullname,
    )
    from app.managers.next_game_manager import (
        NextGameManager,
    )

    await NextGameManager().announce_and_clear(
        deps.bridge(context),
        tm,
        chat.id,
        lang,
    )
    url = deps.join_url(chat.id)
    keyboard = build_join_keyboard(tm, lang, url)
    mention_tpl = load_json(URL_TEMPLATES)[
        "user_mention_html"
    ]
    mention = str(mention_tpl).format(
        user_id=user.id,
        name=fullname,
    )
    caption = tm.get(info.start_text_key, lang, mention)
    caption = f"{caption}\n{tm.get('StartGameFooter', lang)}"
    if group.settext_start:
        caption = f"{caption}\n{group.settext_start}"
    bridge = deps.bridge(context)
    video_id: int | None = None
    gif = group.start_gif or str(
        load_json(URL_TEMPLATES).get(
            "default_start_gif",
            "",
        )
    )
    if gif:
        try:
            video_id = await bridge.send_animation(
                chat.id,
                gif,
                caption,
                reply_markup=keyboard,
            )
        except BadRequest:
            await bridge.send_text(
                chat.id,
                tm.get("NotBotEnableGifOnGroup", lang),
            )
            video_id = await bridge.send_text(
                chat.id,
                caption,
                reply_markup=keyboard,
            )
    else:
        video_id = await bridge.send_text(
            chat.id,
            caption,
            reply_markup=keyboard,
        )
    keys = RedisKeySpace()
    redis = await get_redis()
    key = keys.game_hash(chat.id)
    await redis.hset(
        key,
        keys.field("start_game_at"),
        str(int(time())),
    )
    await _track_edit(chat.id, video_id)
    zero = tm.get("players_header_zero", lang)
    list_id = await bridge.send_text(chat.id, zero)
    await redis.hset(
        key,
        keys.field("player_list_msg"),
        str(list_id),
    )
    if group.pin_player_message:
        try:
            await bridge.pin(chat.id, list_id)
        except Exception:
            pass
    log_game_event(
        "start_game",
        chat_id=chat.id,
        user_id=user.id,
        game_id=game_id,
        phase="join",
        mode=mode,
    )


async def _track_delete(chat_id: int, message_id: int) -> None:
    """Append message id to deleteMessage list."""
    keys = RedisKeySpace()
    redis = await get_redis()
    key = keys.game_hash(chat_id)
    field = keys.field("delete_message")
    raw = await redis.hget(key, field)
    data = json.loads(raw) if raw else []
    if not isinstance(data, list):
        data = []
    data.append(message_id)
    await redis.hset(key, field, json.dumps(data))


async def _track_edit(chat_id: int, message_id: int) -> None:
    """Append message id to EditMarkup list."""
    keys = RedisKeySpace()
    redis = await get_redis()
    key = keys.game_hash(chat_id)
    field = keys.field("edit_markup")
    raw = await redis.hget(key, field)
    data = json.loads(raw) if raw else []
    if not isinstance(data, list):
        data = []
    data.append(message_id)
    await redis.hset(key, field, json.dumps(data))
