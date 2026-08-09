"""Black team overpower formula (black > rosta+fire+monafeq)."""

from __future__ import annotations

from collections import Counter

from app.managers.win_judge import WinJudge


def _judge() -> WinJudge:
    return WinJudge()


def test_black_wins_when_strictly_greater_than_threats() -> None:
    counts = Counter({"black": 2, "rosta": 1, "Firefighter": 0, "monafeq": 0})
    assert _judge()._black_overpower(counts) is True


def test_black_does_not_win_on_tie() -> None:
    counts = Counter({"black": 2, "rosta": 1, "Firefighter": 1, "monafeq": 0})
    assert _judge()._black_overpower(counts) is False


def test_black_requires_wolf_vampire_ferqe_to_be_zero() -> None:
    counts = Counter({"black": 5, "rosta": 1, "wolf": 1})
    assert _judge()._black_overpower(counts) is False
    counts = Counter({"black": 5, "rosta": 1, "vampire": 1})
    assert _judge()._black_overpower(counts) is False
    counts = Counter({"black": 5, "rosta": 1, "ferqeTeem": 1})
    assert _judge()._black_overpower(counts) is False


def test_black_zero_never_wins() -> None:
    counts = Counter({"black": 0, "rosta": 0})
    assert _judge()._black_overpower(counts) is False
