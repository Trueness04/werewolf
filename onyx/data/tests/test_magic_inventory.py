"""Unit tests for magic inventory mapping."""

from app.managers.magic_inventory import (
    EFFECT_TO_SHOP,
    SHOP_TO_EFFECT,
)


def test_shop_to_effect_roundtrip() -> None:
    assert SHOP_TO_EFFECT["MajikReveal"] == "MajiKhabar"
    assert SHOP_TO_EFFECT["MajikProtect"] == "MajiKHil"
    assert SHOP_TO_EFFECT["MajikSilence"] == "MajiKGhost"
    assert SHOP_TO_EFFECT["MajikSear"] == "MajikSear"


def test_effect_to_shop_primary() -> None:
    assert EFFECT_TO_SHOP["MajiKhabar"] == "MajikReveal"
    assert EFFECT_TO_SHOP["MajiKHil"] == "MajikProtect"
    assert EFFECT_TO_SHOP["MajiKGhost"] == "MajikSilence"
    assert EFFECT_TO_SHOP["MajikSear"] == "MajikSear"


def test_player_won_villager() -> None:
    from app.managers.achievement_rewards import (
        _player_won,
    )

    assert _player_won("wolf", "role_wolf") is True
    assert _player_won("wolf", "role_pishgo") is False
    assert _player_won("rosta", "role_pishgo") is True
    assert _player_won("rosta", "role_wolf") is False
