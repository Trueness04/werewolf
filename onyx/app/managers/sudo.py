"""Sudo helpers — allowlist + config + audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.paths import CONFIG_DATA
from app.config.settings import get_settings
from app.database.models.admin import AdminAuditRow
from app.database.session import session_scope

SUDO_CFG = CONFIG_DATA / "sudo.json"


def load_sudo_cfg() -> dict[str, Any]:
    """Load sudo.json feature flags."""
    if not SUDO_CFG.is_file():
        return {
            "charge_live": False,
            "manual_grants_enabled": True,
            "sponsor_lock_default": False,
        }
    return json.loads(
        Path(SUDO_CFG).read_text(encoding="utf-8")
    )


def save_sudo_cfg(data: dict[str, Any]) -> None:
    """Persist sudo.json."""
    Path(SUDO_CFG).write_text(
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def is_sudo(user_id: int) -> bool:
    """True if Telegram user_id is in SUDO_IDS."""
    return int(user_id) in get_settings().sudo_id_set()


async def audit(
    actor_id: int,
    action: str,
    *,
    target_user_id: int | None = None,
    detail: dict | None = None,
) -> None:
    """Append admin audit row."""
    async with session_scope() as session:
        session.add(
            AdminAuditRow(
                actor_id=actor_id,
                action=action,
                target_user_id=target_user_id,
                detail=json.dumps(
                    detail or {},
                    ensure_ascii=False,
                ),
            )
        )
