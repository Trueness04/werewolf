"""Kill flow + redis flag toggles for the senior panel."""

from __future__ import annotations

from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.handlers import deps
from app.handlers.callback_safe import answer_safe
from app.managers.end_game_manager import EndGameManager
from app.managers.game_event import log_game_event
from app.managers.logger_manager import get_logger


def _toggle_field(action: str, panel: dict[str, bool]) -> tuple[str | None,
    bool]:
    """Map a toggle action to its redis field and current value."""
    if action == "magic":
        return ("magic_allowed", panel["magic_allowed"])
    if action == "mute":
        return ("mute_die", panel["mute_die"])
    if action == "secret":
        return ("secret_vote", panel["secret_vote"])
    if action == "vamp":
        return ("vampire_role_on", panel["vampire_on"])
    return ("bloodthirsty_role_on", panel["blood_on"])


def _is_locked_action(action: str) -> bool:
    """True for actions blocked once roles are locked."""
    return action in frozenset(("vamp", "blood"))


async def _locked_answer(
    query: Any,
    tm: Any,
    lang: str,
    chat_id: int,
) -> None:
    """Answer with the roles-locked notice."""
    try:
        await answer_safe(
            query,
            tm.get(
                "SessionSeniorLocked",
                lang,
                bundle="lobby",
            ),
        )
    except Exception as exc:
        get_logger().exception(
            "senior_handler.py:.senior_callback" +
            "locked",
            + "answer.chat={}.exc={}",
            chat_id,
            exc,
        )


async def apply_toggle(
    action: str,
    chat_id: int,
    lang: str,
    tm: Any,
    keys: RedisKeySpace,
    query: Any,
) -> bool:
    """Apply one redis flag toggle; False when action not handled."""
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    if _is_locked_action(action):
        from app.managers.session_senior import (
            read_panel_flags,
            roles_locked,
        )

        if await roles_locked(chat_id, keys):
            await _locked_answer(query, tm, lang, chat_id)
            return False
        panel = await read_panel_flags(chat_id, keys)
        field, cur = _toggle_field(action, panel)
        await redis.hset(
            flags,
            keys.field(field),
            "0" if cur else "1",
        )
        return True
    if action not in frozenset(("mute", "magic", "secret")):
        return False
    from app.managers.session_senior import read_panel_flags

    panel = await read_panel_flags(chat_id, keys)
    field, cur = _toggle_field(action, panel)
    await redis.hset(
        flags,
        keys.field(field),
        "0" if cur else "1",
    )
    return True


async def _do_kill(
    chat_id: int,
    user_id: int,
    value: str,
    lang: str,
    tm: Any = None,
    bridge: Any = None,
    keys: RedisKeySpace = None,
    query: Any = None,
) -> None:
    try:
        if value == "ask":
            try:
                text = tm.get(
                    "SessionSeniorKillConfirm",
                    lang,
                    bundle="lobby",
                )
                await answer_safe(query, text)
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: _do_kill ask an" +
                    "swer chat={} exc={}",
                    chat_id,
                    exc,
                )
            return
        if value == "no":
            try:
                await answer_safe(query)
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: _do_kill no ans" +
                    "wer chat={} exc={}",
                    chat_id,
                    exc,
                )
            return
        if value != "yes":
            return
        try:
            await EndGameManager(bridge).kill(
                chat_id,
                by_user_id=user_id,
            )
        except Exception as exc:
            get_logger().exception(
                "senior.do_kill.c={c}.u={u}.e={e}",
                chat_id,
                user_id,
                exc,
            )
            return
        try:
            text = tm.get(
                "SessionSeniorKilled",
                lang,
                bundle="lobby",
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_kill texts " +
                "chat={} exc={}",
                chat_id,
                exc,
            )
            text = "killed"
        try:
            await answer_safe(query, text)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_kill answer" +
                " killed",
                + " chat={} exc={}",
                chat_id,
                exc,
            )
        try:
            await bridge.send_text(user_id, text)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_kill send_t" +
                "ext killed",
                + " chat={} exc={}",
                chat_id,
                exc,
            )
        try:
            log_game_event(
                "session_senior_kill",
                chat_id=chat_id,
                user_id=user_id,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_kill log ch" +
                "at={} exc={}",
                chat_id,
                exc,
            )
    except Exception as exc:
        get_logger().exception(
            "senior_handler.py:._do_kill.outer" +
            "chat={}.user={}.value={}.exc={}",
            chat_id,
            user_id,
            value,
            exc,
        )
