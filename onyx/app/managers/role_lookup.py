"""Role ↔ user helpers (MF-18 / MF-28)."""

from __future__ import annotations

from typing import Any


def get_role_user_id(
    players: list[dict[str, Any]],
    role_id: str,
) -> int | None:
    """Return first living user_id for role, else None."""
    for item in players:
        if item.get("role") != role_id:
            continue
        if not item.get("alive", True):
            continue
        try:
            return int(item["user_id"])
        except (KeyError, TypeError, ValueError):
            return None
    return None


def key_indices_for_role(
    roles: list[str],
    role_id: str,
) -> list[int]:
    """All indices of role_id — index 0 is valid (MF-18)."""
    return [i for i, r in enumerate(roles) if r == role_id]


def first_key_for_role(
    roles: list[str],
    role_id: str,
) -> int | None:
    """First index of role; None if missing (not 0-as-false)."""
    idxs = key_indices_for_role(roles, role_id)
    if not idxs:
        return None
    return idxs[0]
