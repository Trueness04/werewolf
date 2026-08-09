"""BloodMoon suppression unit tests."""

from __future__ import annotations

from app.managers.bloodmoon import (
    BLOOD_MOON_BURN_STEPS,
    burn_if_blood_moon,
)


def test_burn_skips_wolf() -> None:
    ctx = {
        "blood_moon_active": True,
        "players": [
            {
                "user_id": 1,
                "role": "role_wolf",
                "alive": True,
            }
        ],
        "actions": {"1": "2"},
        "deaths": set(),
        "dm_messages": [],
    }
    assert burn_if_blood_moon(ctx, "wolf_team") is True
    assert ctx["dm_messages"]
    assert ctx["dm_messages"][0][1] == (
        BLOOD_MOON_BURN_STEPS["wolf_team"]
    )


def test_vamp_step_not_burned() -> None:
    ctx = {
        "blood_moon_active": True,
        "players": [],
        "actions": {},
        "deaths": set(),
        "dm_messages": [],
    }
    assert burn_if_blood_moon(ctx, "check_vampire") is False


def test_inactive_no_burn() -> None:
    ctx = {
        "blood_moon_active": False,
        "players": [],
        "actions": {},
        "deaths": set(),
        "dm_messages": [],
    }
    assert burn_if_blood_moon(ctx, "wolf_team") is False
