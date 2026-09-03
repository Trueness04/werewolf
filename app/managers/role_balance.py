"""Role weight balancing helpers."""

from __future__ import annotations

from typing import Any

from app.config.paths import ROLE_FILL
from app.config.settings import Settings
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.logger_manager import get_logger
from app.managers.role_setup_manager import (
    RoleBalanceError,
)


def balance_roles(
    roles: list[str],
    *,
    defs: dict[str, Any],
    weights: dict[str, int],
    settings: Settings,
) -> list[str]:
    """Retry until weights within tolerance."""
    log = get_logger()
    fill = load_json(ROLE_FILL)
    tol = int(settings.balance_tolerance)
    if len(roles) <= int(fill["small_game_max_players"]):
        tol = max(tol, int(fill["small_game_tolerance"]))
    max_try = int(settings.role_balance_max_attempts)
    max_v = max(
        int(fill["min_villagers"]),
        int(len(roles) * float(fill["max_villager_ratio"])),
    )
    current = list(roles)
    for attempt in range(max_try):
        wolf_w, village_w = _team_weights(
            current,
            defs,
            weights,
        )
        diff = abs(wolf_w - village_w)
        log.debug(
            "balance_try a={a} w={w} v={v} d={d}",
            a=attempt,
            w=wolf_w,
            v=village_w,
            d=diff,
        )
        if diff <= tol:
            log_game_event(
                "role_balance_ok",
                attempt=attempt,
                wolf_w=wolf_w,
                village_w=village_w,
            )
            return current
        before = list(current)
        if wolf_w > village_w:
            current = swap_one(
                current,
                defs,
                from_team="wolf",
                to_role="role_villager",
            )
        else:
            vcount = sum(
                1 for r in current if r == "role_villager"
            )
            if vcount >= max_v:
                break
            current = downgrade_heaviest(
                current,
                defs,
                weights,
            )
        if current == before:
            break
    wolf_w, village_w = _team_weights(
        current,
        defs,
        weights,
    )
    if abs(wolf_w - village_w) <= tol + 5:
        return current
    log_game_event(
        "role_balance_soft_ok",
        wolf_w=wolf_w,
        village_w=village_w,
    )
    return current


def _team_weights(
    roles: list[str],
    defs: dict[str, Any],
    weights: dict[str, int],
) -> tuple[int, int]:
    """Return (enemy_weight, village_weight)."""
    from app.config.paths import ROLE_BALANCE_BUCKETS
    from collections import defaultdict

    cfg = load_json(ROLE_BALANCE_BUCKETS)
    map_b = cfg.get("buckets") or {}
    enemy_keys = set(cfg.get("enemy") or [])
    village_keys = set(cfg.get("village") or [])
    tallies: dict[str, int] = defaultdict(int)
    for rid in roles:
        weight = int(weights.get(rid, 0))
        bucket = str(map_b.get(rid) or "")
        if not bucket:
            if defs.get(rid, {}).get("team") == "wolf":
                bucket = "wolf"
            else:
                bucket = "rosta"
        if bucket == "skip":
            continue
        tallies[bucket] += weight
    # MF-10: blod accumulates independent of vampire
    enemy = sum(tallies[k] for k in enemy_keys)
    village = sum(tallies[k] for k in village_keys)
    _ = defs
    return enemy, village


def downgrade_heaviest(
    roles: list[str],
    defs: dict[str, Any],
    weights: dict[str, int],
) -> list[str]:
    """Replace heaviest non-wolf with villager."""
    best_i, best_w = -1, -1
    for idx, rid in enumerate(roles):
        if defs[rid]["team"] == "wolf":
            continue
        if rid == "role_villager":
            continue
        weight = weights.get(rid, 0)
        if weight > best_w:
            best_w, best_i = weight, idx
    if best_i < 0:
        return roles
    out = list(roles)
    out[best_i] = "role_villager"
    return out


def swap_one(
    roles: list[str],
    defs: dict[str, Any],
    *,
    from_team: str,
    to_role: str,
) -> list[str]:
    """Replace one role from team with to_role."""
    out = list(roles)
    for idx, rid in enumerate(out):
        if str(defs[rid]["team"]) != from_team:
            continue
        if defs[rid].get("unique"):
            continue
        out[idx] = to_role
        return out
    for idx, rid in enumerate(out):
        if str(defs[rid]["team"]) == from_team:
            out[idx] = to_role
            return out
    return out
