"""Mighty white wolf + end fillers smoke."""

from __future__ import annotations

from importlib import import_module

from app.managers.json_loader import load_json
from app.managers.role_pool_fillers import (
    append_end_fillers,
    density_sg,
    inject_vampires,
)
from app.config.paths import ROLES_JSON


def test_mighty_white_wolf_night_active() -> None:
    roles = load_json(ROLES_JSON)["roles"]
    row = next(
        r
        for r in roles
        if r["role_id"] == "role_mighty_white_wolf"
    )
    assert row["night1_active"] is True
    assert row["action_kind"] == "kill_non_wolf"
    assert row.get("mighty_stub") is None


def test_no_bomber_role() -> None:
    roles = load_json(ROLES_JSON)["roles"]
    ids = {r["role_id"] for r in roles}
    assert "role_Bomber" not in ids


def test_sg_and_fillers() -> None:
    assert density_sg(12) == 5
    assert density_sg(20) == 6
    out = append_end_fillers(
        ["role_wolf", "role_shekar"],
        12,
        "Normal",
    )
    assert out.count("role_feramason") == 2
    assert out.count("role_ferqe") >= 2
    mighty = append_end_fillers(
        ["role_wolf"],
        12,
        "Mighty",
    )
    assert "role_feramason" not in mighty


def test_vampire_inject_mighty() -> None:
    out = inject_vampires(["role_wolf"], 25, "Mighty")
    assert out.count("role_vampire") >= 5


def test_registry_loads_mighty() -> None:
    Reg = import_module(
        "app.class.roles.registry"
    ).RoleRegistry
    defs = Reg().all_definitions()
    assert defs["role_mighty_white_wolf"]["team"] == (
        "wolf"
    )
