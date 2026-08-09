"""Group /config MVP (PHP CM_Config subset)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.handlers.callback_safe import answer_safe
from app.config.paths import CALLBACK_TEMPLATES
from app.database.session import session_scope
from app.filters import game_filters
from app.handlers import deps
from app.keyboards.inline.config_keyboard import (
    build_config_keyboard,
    build_flavor_keyboard,
    build_max_player_keyboard,
)
from app.managers.flavor_packs import is_known_pack
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import GroupInactive
from app.managers.json_loader import load_json
from app.managers.group_limits import max_players_of
from sqlalchemy import select
from app.database.models.group import GroupRow


async def config_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send config panel to admin PV."""
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return
    if not await game_filters.is_group(update):
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    if not await game_filters.is_admin(update, context):
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get("NotAllowForUser", lang),
        )
        return
    try:
        group = await deps.state_mgr().ensure_group_active(
            chat.id,
        )
    except GroupInactive:
        return
    if group is None:
        return
    markup = _keyboard(tm, lang, chat.id, group)
    await context.bot.send_message(
        chat_id=user.id,
        text=tm.get(
            "ConfigSendPrvaite",
            lang,
            bundle="lobby",
        ),
        reply_markup=markup,
    )
    await context.bot.send_message(
        chat_id=chat.id,
        text=tm.get(
            "ConfigSendPrvaite",
            lang,
            bundle="lobby",
        ),
    )
    log_game_event(
        "config_open",
        chat_id=chat.id,
        user_id=user.id,
    )


async def config_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Apply config toggle / max / flavor / done."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await answer_safe(query)
    tpl = load_json(CALLBACK_TEMPLATES)
    if not query.data.startswith(
        str(tpl["config_prefix"])
    ):
        return
    parts = query.data.split(":")
    if len(parts) < 4:
        return
    try:
        chat_id = int(parts[1])
        action = parts[2]
        value = parts[3]
    except ValueError:
        return
    member = await context.bot.get_chat_member(
        chat_id,
        user.id,
    )
    if str(member.status) not in {
        "creator",
        "administrator",
    }:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    group = await deps.state_mgr().ensure_group_active(
        chat_id,
    )
    if group is None:
        return
    if action == "done":
        await query.edit_message_text(
            tm.get("config_done", lang, bundle="lobby")
        )
        return
    if action == "maxmenu":
        await query.edit_message_reply_markup(
            reply_markup=build_max_player_keyboard(
                chat_id
            ),
        )
        return
    if action == "flavor":
        current = str(
            getattr(group, "text_mode", "general")
            or "general"
        )
        await query.edit_message_reply_markup(
            reply_markup=build_flavor_keyboard(
                tm,
                lang,
                chat_id,
                current,
            ),
        )
        return
    if action == "menu":
        await query.edit_message_reply_markup(
            reply_markup=_keyboard(
                tm,
                lang,
                chat_id,
                group,
            ),
        )
        return
    await _apply(group, action, value)
    group = await deps.state_mgr().ensure_group_active(
        chat_id,
    )
    if group is None:
        return
    if action == "setflavor":
        tip = tm.get(
            "gameModeTochange",
            lang,
            bundle="main",
        )
        await query.edit_message_text(
            tip,
            reply_markup=_keyboard(
                tm,
                lang,
                chat_id,
                group,
            ),
        )
        return
    await query.edit_message_reply_markup(
        reply_markup=_keyboard(
            tm,
            lang,
            chat_id,
            group,
        ),
    )


def config_pattern() -> str:
    """Pattern for config callbacks."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["config_handler_pattern"])


def _keyboard(tm, lang, chat_id, group):
    return build_config_keyboard(
        tm,
        lang,
        chat_id,
        allow_flee=bool(
            getattr(group, "allow_flee", True)
        ),
        allow_extend=bool(group.allow_extend),
        pin=bool(group.pin_player_message),
        vamp=bool(group.vampire_role_on),
        blood=bool(group.bloodthirsty_role_on),
        secret_vote=bool(
            getattr(group, "secret_vote", False)
        ),
        mute_die=bool(
            getattr(group, "mute_die", False)
        ),
        max_players=max_players_of(
            group,
            deps.settings(),
        ),
        text_mode=str(
            getattr(group, "text_mode", "general")
            or "general"
        ),
    )


async def _apply(group, action: str, value: str) -> None:
    async with session_scope() as session:
        stmt = select(GroupRow).where(
            GroupRow.chat_id == int(group.chat_id)
        )
        row = (
            await session.execute(stmt)
        ).scalar_one_or_none()
        if row is None:
            return
        if action == "flee":
            row.allow_flee = not bool(
                getattr(row, "allow_flee", True)
            )
        elif action == "extend":
            row.allow_extend = not bool(row.allow_extend)
        elif action == "pin":
            row.pin_player_message = not bool(
                row.pin_player_message
            )
        elif action == "vamp":
            row.vampire_role_on = not bool(
                row.vampire_role_on
            )
        elif action == "blood":
            row.bloodthirsty_role_on = not bool(
                row.bloodthirsty_role_on
            )
        elif action == "secret":
            row.secret_vote = not bool(
                getattr(row, "secret_vote", False)
            )
        elif action == "mute":
            row.mute_die = not bool(
                getattr(row, "mute_die", False)
            )
        elif action == "setflavor":
            if is_known_pack(value):
                row.text_mode = value
        elif action == "max":
            from app.managers.group_limits import (
                clamp_max_players,
            )

            row.max_players = clamp_max_players(
                int(value)
            )
