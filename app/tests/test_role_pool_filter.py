"""role_pool_filter: N thresholds + Vampire bypass, and SG fillers."""

from __future__ import annotations

from collections import Counter

from app.managers.role_pool_fillers import (
    append_end_fillers,
    density_sg,
    inject_vampires,
)
from app.managers.role_pool_filter import filter_pool_by_n


def test_filter_drops_roles_below_min_players() -> None:
    pool = ["role_wolf", "role_shekar", "role_lucifer"]
    out = filter_pool_by_n(pool, 10, "Normal")
    assert out == ["role_wolf"]


def test_filter_includes_role_once_threshold_met() -> None:
    pool = ["role_wolf", "role_shekar", "role_lucifer"]
    out = filter_pool_by_n(pool, 11, "Normal")
    assert out == ["role_wolf", "role_shekar"]


def test_vampire_mode_bypasses_min_players() -> None:
    pool = ["role_vampire", "role_Bloodthirsty"]
    # role_vampire/Bloodthirsty normally need 25 players.
    excluded = filter_pool_by_n(pool, 7, "Normal")
    bypassed = filter_pool_by_n(pool, 7, "Vampire")
    assert excluded == []
    assert bypassed == pool


def test_density_sg_thresholds() -> None:
    assert density_sg(19) == 5
    assert density_sg(20) == 6


def test_append_end_fillers_counts() -> None:
    out = append_end_fillers(["role_shekar"], 5, "Normal")
    counts = Counter(out)
    assert counts["role_shekar"] == 1
    assert counts["role_feramason"] == 2
    assert counts["role_ferqe"] == 2
    assert counts["role_villager"] == 1


def test_inject_vampires_only_for_vampire_and_large_mighty() -> None:
    normal_out = inject_vampires(["role_villager"], 30, "Normal")
    vampire_out = inject_vampires(["role_villager"], 10, "Vampire")
    assert normal_out == ["role_villager"]
    assert vampire_out.count("role_vampire") == 2
