"""End-of-pool role fillers (sprint-09 §3.7)."""

from __future__ import annotations

from app.config.paths import ROLE_FILL
from app.managers.json_loader import load_json


def density_sg(n: int) -> int:
    """SG: 5 if N<20 else 6."""
    fill = load_json(ROLE_FILL)
    thr = int(fill.get("sg_threshold", 20))
    if n < thr:
        return int(fill.get("sg_small", 5))
    return int(fill.get("sg_large", 6))


def append_end_fillers(
    roles: list[str],
    n: int,
    mode: str,
    *,
    ferqe_on: bool = True,
    feramason_on: bool = True,
    rosta_on: bool = True,
) -> list[str]:
    """Append feramason/ferqe/rosta copies before slice."""
    out = list(roles)
    sg = density_sg(n)
    extra = max(0, int(round(n / sg)))
    if mode != "Mighty" and feramason_on:
        out.extend(["role_feramason", "role_feramason"])
    if "role_shekar" in out:
        out.extend(["role_ferqe", "role_ferqe"])
    if n > 11 and ferqe_on:
        out.extend(["role_ferqe"] * extra)
    if mode != "Mighty" and rosta_on:
        out.extend(["role_villager"] * extra)
    return out


def inject_vampires(
    roles: list[str],
    n: int,
    mode: str,
    *,
    vamp_on: bool = True,
) -> list[str]:
    """Add Vampire copies for Vampire / Mighty."""
    if not vamp_on:
        return list(roles)
    out = list(roles)
    if mode == "Vampire":
        count = max(1, n // 5)
    elif mode == "Mighty" and n >= 25:
        count = max(1, n // 5)
    else:
        return out
    have = sum(1 for r in out if r == "role_vampire")
    need = max(0, count - have)
    out.extend(["role_vampire"] * need)
    return out

