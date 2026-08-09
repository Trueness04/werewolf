"""Heuristic decision helpers for AI agents."""

from __future__ import annotations

import random
from typing import Any


def alive_others(
    snapshot: dict[str, Any],
    self_id: int,
) -> list[dict[str, Any]]:
    """Alive players excluding self."""
    out: list[dict[str, Any]] = []
    for item in snapshot.get("players", []):
        if int(item["user_id"]) == self_id:
            continue
        if not item.get("alive", True):
            continue
        out.append(item)
    return out


def pick_random_id(
    players: list[dict[str, Any]],
) -> int | None:
    """Random user_id from player dicts."""
    if not players:
        return None
    return int(random.choice(players)["user_id"])


def night_choice(
    snapshot: dict[str, Any],
    yes_chance: float,
) -> str | None:
    """Choose night action from role target type."""
    role = snapshot.get("role") or {}
    if not role.get("night1_active"):
        return None
    self_id = int(snapshot["self_id"])
    ttype = str(role.get("target_type") or "none")
    others = alive_others(snapshot, self_id)
    team = str(role.get("team") or "")
    if ttype == "yes_no":
        if random.random() < yes_chance:
            return "yes"
        return "no"
    if ttype != "single_target":
        return None
    if team == "wolf":
        prey = [
            p
            for p in others
            if p.get("team") != "wolf"
        ]
        return _as_str(pick_random_id(prey or others))
    return _as_str(pick_random_id(others))


def day_choice(
    snapshot: dict[str, Any],
    yes_chance: float,
    gunner_chance: float,
    spy_chance: float,
) -> str | None:
    """Choose day action for current role."""
    role_id = str(snapshot.get("role_id") or "")
    self_id = int(snapshot["self_id"])
    others = alive_others(snapshot, self_id)
    day_cfg = snapshot.get("day_roles") or {}
    immediate = set(day_cfg.get("immediate", []))
    deferred = set(day_cfg.get("deferred", []))
    if role_id in immediate:
        if random.random() < yes_chance:
            return "yes"
        return "no"
    if role_id == "role_tofangdar":
        if random.random() >= gunner_chance:
            return None
        return _as_str(pick_random_id(others))
    if role_id == "role_Spy":
        if random.random() >= spy_chance:
            return None
        return _as_str(pick_random_id(others))
    if role_id in deferred:
        return _as_str(pick_random_id(others))
    return None


def vote_choice(snapshot: dict[str, Any]) -> int | None:
    """Pick a lynch target."""
    self_id = int(snapshot["self_id"])
    others = alive_others(snapshot, self_id)
    team = str(
        (snapshot.get("role") or {}).get("team") or ""
    )
    if team == "wolf":
        prey = [
            p
            for p in others
            if p.get("team") != "wolf"
        ]
        return pick_random_id(prey or others)
    return pick_random_id(others)


def _as_str(value: int | None) -> str | None:
    """Convert optional id to string choice."""
    if value is None:
        return None
    return str(value)
