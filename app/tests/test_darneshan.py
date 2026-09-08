"""DarNeshan night mark unit tests."""

from __future__ import annotations

import asyncio

from app.managers.darneshan_resolve import (
    burn_mark_if_target_dead,
    resolve_dar_neshan_mark,
)


def _ctx(**kwargs):
    base = {
        "chat_id": 1,
        "night_no": 2,
        "players": [],
        "actions": {},
        "roles": {},
        "messages": [],
        "dm_messages": [],
        "deaths": set(),
        "flags_out": {},
        "flags": {},
        "blood_moon_active": False,
    }
    base.update(kwargs)
    return base


def test_mark_sets_flags() -> None:
    players = [
        {
            "user_id": 10,
            "role": "role_DarNeshan",
            "team": "cult",
            "alive": True,
            "fullname": "DN",
        },
        {
            "user_id": 20,
            "role": "role_villager",
            "team": "villager",
            "alive": True,
            "fullname": "V",
        },
    ]
    ctx = _ctx(
        players=players,
        actions={"10": "20"},
        roles={
            "10": "role_DarNeshan",
            "20": "role_villager",
        },
    )

    async def _run():
        await resolve_dar_neshan_mark(ctx)

    asyncio.run(_run())
    assert ctx["flags_out"]["darneshan_mark_target"] == "20"
    assert ctx["flags_out"]["darneshan_mark_by"] == "10"
    assert ctx["dm_messages"]


def test_skip_cult_target() -> None:
    players = [
        {
            "user_id": 10,
            "role": "role_DarNeshan",
            "team": "cult",
            "alive": True,
            "fullname": "DN",
        },
        {
            "user_id": 20,
            "role": "role_ferqe",
            "team": "cult",
            "alive": True,
            "fullname": "F",
        },
    ]
    ctx = _ctx(
        players=players,
        actions={"10": "20"},
        roles={
            "10": "role_DarNeshan",
            "20": "role_ferqe",
        },
    )
    asyncio.run(resolve_dar_neshan_mark(ctx))
    assert "darneshan_mark_target" not in ctx["flags_out"]


def test_burn_on_night_death() -> None:
    ctx = _ctx(
        darneshan_mark_target="20",
        darneshan_mark_by="10",
        deaths={20},
    )
    burn_mark_if_target_dead(ctx)
    assert ctx["flags_out"]["darneshan_mark_target"] == ""
    assert ctx["dm_messages"]
