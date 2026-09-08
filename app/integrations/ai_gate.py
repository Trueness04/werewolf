"""Guarded access points to the optional AI package.

The game must run with the top-level ``AI/`` package completely
absent (AI Player decoupling). Every former direct AI-package
import call site goes through this module: when
``settings.enable_bot_to_bot`` is off — or the package is simply
not installed — the helper returns a clean no-op coroutine (or
``None``) and logs a single warning line naming module + context.
No bare excepts, no silent swallows.
"""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from typing import Any, Awaitable, Callable

from app.config.settings import get_settings
from app.managers.logger_manager import get_logger

AI_ABSENT_LOG_PREFIX = "ai_package_absent"


def ai_available() -> bool:
    """True when AI is enabled and the package is importable."""
    if not get_settings().enable_bot_to_bot:
        return False
    try:
        return find_spec("AI") is not None
    except (ImportError, ValueError):
        return False


def _warn_absent(module: str, context: str) -> None:
    get_logger().warning(
        "{}.module={}.context={}.skipped",
        AI_ABSENT_LOG_PREFIX,
        module,
        context,
    )


def _ai_feature(
    module: str,
    attr: str,
    context: str,
) -> Callable[..., Awaitable[Any]] | None:
    """Import module.attr from the optional AI package.

    Returns the callable, or None (after one logged warning)
    when AI is disabled or the package/module is absent.
    """
    if not ai_available():
        _warn_absent(module, context)
        return None
    try:
        mod = import_module(module)
        return getattr(mod, attr)
    except ImportError as exc:
        get_logger().warning(
            "{}.m={}.ctx={}.e={}",
            AI_ABSENT_LOG_PREFIX,
            module,
            context,
            str(exc),
        )
        return None


async def _noop(*args: Any, **kwargs: Any) -> None:
    return None


def ai_callable(
    module: str,
    attr: str,
    context: str,
) -> Callable[..., Awaitable[Any]]:
    """AI coroutine factory; a no-op when AI is unavailable.

    Never returns None, so call sites can simply
    ``await ai_callable(...)()``.
    """
    fn = _ai_feature(module, attr, context)
    if fn is None:
        return _noop
    return fn


def ai_class(
    module: str,
    attr: str,
    context: str,
) -> Any | None:
    """AI class/symbol accessor; None when unavailable.

    For sync AI symbols (e.g. AgentRegistry). Call sites
    must handle the None return explicitly.
    """
    return _ai_feature(module, attr, context)


async def maybe_run_ai(
    module: str,
    attr: str,
    context: str,
    /,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Run an AI coroutine guarded; None when AI is unavailable."""
    fn = _ai_feature(module, attr, context)
    if fn is None:
        return None
    return await fn(*args, **kwargs)
