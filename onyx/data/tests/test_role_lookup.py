"""Tests for MF-18/28 role lookup helpers."""

from app.managers.role_lookup import (
    first_key_for_role,
    get_role_user_id,
    key_indices_for_role,
)


def test_first_key_index_zero() -> None:
    roles = ["role_wolf", "role_villager"]
    assert first_key_for_role(roles, "role_wolf") == 0
    assert first_key_for_role(roles, "role_pishgo") is None


def test_key_indices_include_zero() -> None:
    roles = ["role_wolf", "role_wolf", "role_pishgo"]
    assert key_indices_for_role(roles, "role_wolf") == [
        0,
        1,
    ]


def test_get_role_user_id_none() -> None:
    players = [
        {"user_id": 1, "role": "role_wolf", "alive": True},
    ]
    assert get_role_user_id(players, "role_pishgo") is None
    assert get_role_user_id(players, "role_wolf") == 1
