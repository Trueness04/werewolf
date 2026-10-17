"""MF-10 independent blod vs vampire buckets."""

from app.managers.role_balance import _team_weights


def test_blood_and_vamp_add_separately():
    defs = {
        "role_vampire": {"team": "solo"},
        "role_Bloodthirsty": {"team": "solo"},
        "role_villager": {"team": "villager"},
        "role_wolf": {"team": "wolf"},
    }
    weights = {
        "role_vampire": 9,
        "role_Bloodthirsty": 10,
        "role_villager": 2,
        "role_wolf": 10,
    }
    roles = [
        "role_vampire",
        "role_Bloodthirsty",
        "role_villager",
        "role_wolf",
    ]
    enemy, village = _team_weights(roles, defs, weights)
    # vamp 9 + blood 10 + wolf 10 = 29 enemy; villager 2
    assert enemy == 29
    assert village == 2


def test_lucifer_skipped():
    defs = {
        "role_lucifer": {"team": "solo"},
        "role_wolf": {"team": "wolf"},
        "role_villager": {"team": "villager"},
    }
    weights = {
        "role_lucifer": 17,
        "role_wolf": 10,
        "role_villager": 2,
    }
    e1, v1 = _team_weights(
        ["role_wolf", "role_villager"],
        defs,
        weights,
    )
    e2, v2 = _team_weights(
        ["role_wolf", "role_villager", "role_lucifer"],
        defs,
        weights,
    )
    assert (e1, v1) == (e2, v2)
