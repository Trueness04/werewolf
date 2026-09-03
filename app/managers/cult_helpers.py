"""Cult vote bucket and attempt chance helpers."""

from __future__ import annotations

from random import SystemRandom
from typing import Any

from app.config.paths import CONFIG_DATA
from app.managers.json_loader import load_json
from app.managers.night_village import player

_RULES = CONFIG_DATA / "cult_rules.json"


def cult_rules() -> dict[str, Any]:
    """Load cult_rules.json."""
    return load_json(_RULES)


def ferqe_bucket(
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    """Alive players in operational ferqe vote bucket."""
    roles = set(cult_rules()["vote_bucket"])
    return [
        p
        for p in ctx["players"]
        if p.get("alive", True)
        and str(p.get("role") or "") in roles
    ]


def cult_attempt_ok(
    role: str,
    *,
    convert_buff: bool,
) -> bool:
    """True if CultAttemp succeeds for role."""
    rules = cult_rules()
    buff = 20 if convert_buff else 0
    if role in rules["certain"]:
        return True
    if role in rules["resistant"]:
        return False
    chance = rules["chance"].get(role)
    if chance is None:
        return False
    return SystemRandom().randrange(100) < (
        int(chance) + buff
    )


def pick_cult_target(
    ctx: dict[str, Any],
) -> tuple[int | None, int | None]:
    """Return (target_id, visitor_id) from votes."""
    bucket = ferqe_bucket(ctx)
    if not bucket:
        return None, None
    actions = ctx["actions"]
    if len(bucket) > 1:
        from collections import Counter

        votes: list[int] = []
        for item in bucket:
            raw = actions.get(str(item["user_id"]))
            if not raw:
                continue
            try:
                votes.append(int(raw))
            except ValueError:
                continue
        if not votes:
            return None, None
        target, _ = Counter(votes).most_common(1)[0]
        visitor = int(bucket[-1]["user_id"])
        return target, visitor
    only = bucket[0]
    raw = actions.get(str(only["user_id"]))
    if not raw:
        return None, None
    return int(raw), int(only["user_id"])


def convert_to_ferqe(
    ctx: dict[str, Any],
    target_id: int,
) -> None:
    """Immediate cult convert (not delayed gas)."""
    victim = player(ctx, target_id)
    if victim is None:
        return
    victim["role"] = "role_ferqe"
    victim["team"] = "cult"
    ctx["roles"][str(target_id)] = "role_ferqe"
    ctx["messages"].append("CultConvertYou")
    ctx["messages"].append("CultJoin")
