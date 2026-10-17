"""force_role_pairs: non_vg-safe injects and forced pairs."""

from __future__ import annotations

from collections import Counter
from random import Random

from app.managers.role_forced import force_role_pairs


def test_inject_never_overwrites_non_vg_slot() -> None:
    """ferqe (non_vg) present without shekar injects into villager."""
    roles = ["role_wolf", "role_ferqe", "role_villager"]
    out = force_role_pairs(roles, Random(1))
    assert out.count("role_ferqe") == 1
    assert out.count("role_wolf") == 1
    assert out.count("role_shekar") == 1
    assert "role_villager" not in out


def test_ferqe_without_shekar_injects_shekar() -> None:
    """Rule G/H: ferqe present, shekar missing -> shekar injected."""
    roles = ["role_wolf", "role_ferqe", "role_villager", "role_villager"]
    out = force_role_pairs(roles, Random(2))
    assert Counter(out)["role_shekar"] == 1
    assert Counter(out)["role_ferqe"] == 1


def test_vampire_triangle_completes_kalantar_and_bloodthirsty() -> None:
    """Rules D-F: lone vampire gains kalantar + Bloodthirsty."""
    roles = ["role_wolf", "role_vampire", "role_villager", "role_villager"]
    out = force_role_pairs(roles, Random(3))
    counts = Counter(out)
    assert counts["role_vampire"] == 1
    assert counts["role_kalantar"] == 1
    assert counts["role_Bloodthirsty"] == 1
    assert counts["role_wolf"] == 1
    assert counts["role_villager"] == 0


def test_wolf_dependent_without_base_wolf_becomes_base_wolf() -> None:
    """Rule A: WolfJadogar alone (no base wolf) is replaced."""
    roles = ["role_WolfJadogar", "role_villager"]
    out = force_role_pairs(roles, Random(4))
    assert "role_WolfJadogar" not in out
    from app.managers.role_pairs import has_base_wolf

    bases = [
        "role_wolf",
        "role_WhiteWolf",
        "role_Alpha",
        "role_Tolle",
        "role_Wolfx",
        "role_WolfGorgine",
        "role_iceWolf",
    ]
    assert has_base_wolf(out, bases)
