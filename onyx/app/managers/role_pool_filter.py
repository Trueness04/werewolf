"""Role pool load + N thresholds (sprint-09)."""

from __future__ import annotations

from app.config.paths import (
    GAME_MODE_ROLES,
    ROLE_POOL_THRESHOLDS,
    WOLF_COUNT_TABLE,
)
from app.managers.json_loader import load_json


def filter_pool_by_n(
    pool: list[str],
    player_count: int,
    mode: str,
) -> list[str]:
    """Drop roles whose min_players exceeds N."""
    raw = load_json(ROLE_POOL_THRESHOLDS)
    mins = {
        str(k): int(v)
        for k, v in (raw.get("min_players") or {}).items()
    }
    bypass = set(
        str(x)
        for x in (raw.get("mode_bypass") or {})
        .get(mode, [])
    )
    out: list[str] = []
    for rid in pool:
        if rid in bypass:
            out.append(rid)
            continue
        if player_count >= mins.get(rid, 0):
            out.append(rid)
    return out


def load_mode_pool(
    mode: str,
    count: int = 0,
) -> list[str]:
    """Return mode pool filtered by N."""
    raw = load_json(GAME_MODE_ROLES)
    if mode not in raw:
        mode = "Normal"
    pool = [str(item) for item in raw[mode]]
    if count <= 0:
        return pool
    return filter_pool_by_n(pool, count, mode)


def lookup_wolf_count(count: int) -> int:
    """Lookup wolf count from table ranges."""
    table = load_json(WOLF_COUNT_TABLE)
    for row in table["ranges"]:
        low = int(row["min_players"])
        high = int(row["max_players"])
        if low <= count <= high:
            return int(row["wolf_count"])
    return 2
