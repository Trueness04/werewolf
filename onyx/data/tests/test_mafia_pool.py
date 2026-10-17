"""Mafia mode pool smoke."""

from app.config.paths import GAME_MODES
from app.managers.json_loader import load_json
from app.managers.role_pool_filter import load_mode_pool


def test_mafia_pool_nonempty():
    pool = load_mode_pool("Mafia", 12)
    assert "role_wolf" in pool
    assert len(pool) >= 3


def test_mafia_min_players():
    modes = load_json(GAME_MODES)["modes"]
    assert "Mafia" in modes
    assert int(modes["Mafia"]["min_players"]) >= 5
    assert "Bomber" not in modes
    assert "Coin" not in modes
