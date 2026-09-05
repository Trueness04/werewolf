"""Role weight balancing helpers."""

from __future__ import annotations

from random import SystemRandom
from typing import Any

from app.config.paths import ROLE_FILL
from app.config.settings import Settings
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.logger_manager import get_logger
from app.managers.role_setup_manager import (
    RoleBalanceError,
)


_RNG = SystemRandom()
_BASELINE_WEIGHT = 2  # role_villager's own weight, used as target


def _pick_fallback(
    current: list[str],
    defs: dict[str, Any],
    weights: dict[str, int],
    fallback_pool: list[str],
    target_weight: int = _BASELINE_WEIGHT,
    required_team: str = "villager",
) -> str:
    """Pick a low-impact role from fallback_pool.

    Filters out unique roles already present in `current`,
    requires defs[rid]["team"] == required_team (so a
    mis-classified entry in the pool config, e.g. a role
    that's actually wolf-aligned, can never silently swap
    into a village-side slot), prefers weight within +-1 of
    target_weight, and always falls back to role_villager if
    the pool is empty/unusable, so this can never crash a game.
    """
    def usable(rid: str) -> bool:
        if rid not in weights:
            return False
        if defs.get(rid, {}).get("team") != required_team:
            return False
        if defs.get(rid, {}).get("unique") and rid in current:
            return False
        return True

    near = [
        rid
        for rid in fallback_pool
        if usable(rid)
        and abs(weights[rid] - target_weight) <= 1
    ]
    if near:
        return _RNG.choice(near)
    any_usable = [rid for rid in fallback_pool if usable(rid)]
    if any_usable:
        return _RNG.choice(any_usable)
    return "role_villager"


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
    fallback_pool = fill.get(
        "balance_fallback_roles", ["role_villager"]
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
                weights,
                from_team="wolf",
                fallback_pool=fallback_pool,
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
                fallback_pool=fallback_pool,
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
    fallback_pool: list[str] | None = None,
) -> list[str]:
    """Replace heaviest non-wolf with a low-impact fallback role."""
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
    pool = fallback_pool or ["role_villager"]
    out[best_i] = _pick_fallback(out, defs, weights, pool)
    return out


def swap_one(
    roles: list[str],
    defs: dict[str, Any],
    weights: dict[str, int],
    *,
    from_team: str,
    fallback_pool: list[str] | None = None,
) -> list[str]:
    """Replace one role from team with a low-impact fallback role."""
    out = list(roles)
    pool = fallback_pool or ["role_villager"]
    for idx, rid in enumerate(out):
        if str(defs[rid]["team"]) != from_team:
            continue
        if defs[rid].get("unique"):
            continue
        out[idx] = _pick_fallback(out, defs, weights, pool)
        return out
    for idx, rid in enumerate(out):
        if str(defs[rid]["team"]) == from_team:
            out[idx] = _pick_fallback(out, defs, weights, pool)
            return out
    return out
