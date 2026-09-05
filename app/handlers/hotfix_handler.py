"""Sudo-only /hotfix — git pull + module reload without rebuild."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from app.managers.game_event import log_game_event
from app.managers.sudo import is_sudo

# Modules that are safe to live-reload (managers + handlers).
# Order: dependencies first, dependents after.
_RELOAD_ORDER: tuple[str, ...] = (
    "app.cache.redis_keys",
    "app.managers.game_state_manager",
    "app.managers.lobby_manager",
    "app.managers.phase_ticker",
    "app.managers.timer_manager",
    "app.managers.night_phase",
    "app.managers.day_phase",
    "app.managers.vote_phase",
    "app.managers.end_game_manager",
    "app.managers.session_senior",
    "app.managers.senior_handler",
    "app.managers.role_distribution_manager",
    "app.managers.role_balance",
    "app.managers.achievement_rewards",
    "app.managers.player_format",
    "app.managers.rank_governor",
    "app.managers.logger_manager",
    "app.handlers.start_game",
    "app.handlers.join_game",
    "app.handlers.kill_game",
    "app.handlers.night_action_handler",
    "app.handlers.day_action_handler",
    "app.handlers.vote_action_handler",
    "app.handlers.players_list",
    "app.handlers.force_start",
    "app.handlers.flee",
    "app.handlers.extend",
    "app.handlers.economy",
    "app.handlers.meta_play",
    "app.handlers.challenge",
    "app.handlers.magic_handler",
    "app.handlers.mode_info",
    "app.handlers.next_game",
    "app.handlers.config_handler",
    "app.handlers.ai_toggle",
    "app.handlers.hotfix_handler",
)


async def _git_pull() -> str:
    """Pull latest from origin/main inside the container."""
    import asyncio

    proc = await asyncio.create_subprocess_exec(
        "git", "-C", "/app", "pull", "--ff-only", "origin", "main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return out.decode(errors="replace").strip()


def _reload_modules() -> list[str]:
    """Reload all tracked modules. Returns list of reloaded names."""
    reloaded: list[str] = []
    for mod_name in _RELOAD_ORDER:
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        try:
            importlib.reload(mod)
            reloaded.append(mod_name)
        except Exception:
            pass
    return reloaded


async def hotfix_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Git pull + reload modules (sudo only)."""
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return
    if not is_sudo(user.id):
        return

    await context.bot.send_message(
        chat_id=chat.id, text="⏳ دریافت آخرین کد...",
    )

    try:
        pull_result = await _git_pull()
    except Exception as exc:
        pull_result = f"خطای git: {exc}"

    reloaded = _reload_modules()
    count = len(reloaded)

    log_game_event(
        "hotfix_applied",
        chat_id=chat.id,
        modules=count,
        pull=pull_result[:200],
    )

    text = (
        f"✅ هات‌فیکس اعمال شد\n"
        f"📦 {count} ماژول ریلود شد\n"
        f"🔄 git: {pull_result[:300]}"
    )
    await context.bot.send_message(chat_id=chat.id, text=text)
