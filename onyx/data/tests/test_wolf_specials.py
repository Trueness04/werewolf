"""Wolf specials depth smoke tests."""

from __future__ import annotations

import asyncio

from app.managers.wolf_specials import (
    resolve_honey,
    resolve_white_wolf,
    resolve_beta_wolf,
)


def _ctx(players, actions=None, roles=None):
    roles = roles or {
        str(p["user_id"]): p["role"] for p in players
    }
    return {
        "players": players,
        "actions": actions or {},
        "roles": roles,
        "messages": [],
        "deaths": set(),
        "flags_out": {},
    }


def test_white_wolf_alone_becomes_wolf() -> None:
    players = [
        {
            "user_id": 1,
            "role": "role_WhiteWolf",
            "team": "wolf",
            "alive": True,
        }
    ]
    ctx = _ctx(players)
    asyncio.run(resolve_white_wolf(ctx))
    assert players[0]["role"] == "role_wolf"


def test_honey_marks_target() -> None:
    players = [
        {
            "user_id": 1,
            "role": "role_Honey",
            "team": "wolf",
            "alive": True,
        },
        {
            "user_id": 2,
            "role": "role_villager",
            "team": "villager",
            "alive": True,
        },
    ]
    ctx = _ctx(players, actions={"1": "2"})
    asyncio.run(resolve_honey(ctx))
    assert ctx["honey_user"] == "2"


def test_beta_mask_set() -> None:
    players = [
        {
            "user_id": 1,
            "role": "role_betaWolf",
            "team": "wolf",
            "alive": True,
        },
        {
            "user_id": 2,
            "role": "role_villager",
            "team": "villager",
            "alive": True,
        },
    ]
    ctx = _ctx(players)
    asyncio.run(resolve_beta_wolf(ctx))
    assert "1" in ctx["beta_masks"]
