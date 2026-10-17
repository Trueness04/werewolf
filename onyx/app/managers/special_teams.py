"""Sprint 05e: bride, lucifer, dynamite night slots."""

from __future__ import annotations

import json
from random import SystemRandom
from typing import Any

from app.config.paths import ROOT
from app.managers.json_loader import load_json
from app.managers.night_village import player

_CHANCES = ROOT / "data" / "config" / "field_chances.json"
_TEAMS = {
    "rosta",
    "wolf",
    "ferqeTeem",
    "vampire",
    "qatel",
}
_NIGHT_STEAL = {
    "role_pishgo",
    "role_Natasha",
    "role_Fereshte",
    "role_enchanter",
    "role_Fool",
    "role_ferqe",
    "role_Honey",
    "role_firefighter",
    "role_IceQueen",
    "role_ngativ",
    "role_vampire",
    "role_Chemist",
}
_DAY_STEAL = {
    "role_Spy",
    "role_Princess",
    "role_tofangdar",
    "role_karagah",
}


def _chance(key: str) -> int:
    """Percent from field_chances."""
    data = load_json(_CHANCES)
    return int(data.get(key, 35))


async def resolve_bride(ctx: dict[str, Any]) -> None:
    """Bride night kill (late slot)."""
    for item in ctx["players"]:
        if item.get("role") != "role_BrideTheDead":
            continue
        if not item.get("alive", True):
            continue
        # Needs living BlackKnight
        bk_alive = any(
            p.get("role") == "role_BlackKnight"
            and p.get("alive", True)
            and int(p["user_id"]) not in ctx["deaths"]
            for p in ctx["players"]
        )
        if not bk_alive:
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        if ctx.get("bard_redirect") is not None:
            tid = int(ctx["bard_redirect"])
        target = player(ctx, tid)
        if target is None:
            ctx.setdefault("seer_notes", []).append(
                (
                    int(item["user_id"]),
                    "",
                    "PlayerDead",
                )
            )
            continue
        ctx["deaths"].add(tid)
        ctx["messages"].append("BrideKill")


def follow_black_knight_death(
    ctx: dict[str, Any],
) -> None:
    """BK death kills living Bride."""
    bk_dead = False
    for p in ctx["players"]:
        if p.get("role") != "role_BlackKnight":
            continue
        uid = int(p["user_id"])
        if not p.get("alive", True) or uid in ctx["deaths"]:
            bk_dead = True
    if not bk_dead:
        return
    for p in ctx["players"]:
        if p.get("role") != "role_BrideTheDead":
            continue
        if not p.get("alive", True):
            continue
        uid = int(p["user_id"])
        if uid in ctx["deaths"]:
            continue
        ctx["deaths"].add(uid)
        ctx["messages"].append("BrideTheDeadBlackDie")


async def resolve_lucifer_team(
    ctx: dict[str, Any],
) -> None:
    """Night0 team lock; night>=1 deceive flags."""
    night = int(ctx.get("night_no") or 0)
    for item in ctx["players"]:
        if item.get("role") != "role_lucifer":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            if night == 0:
                item["team"] = "villager"
                ctx["messages"].append("LuciferTeamRosta")
            continue
        if night == 0:
            team = str(raw)
            if team not in _TEAMS:
                team = "rosta"
            _apply_lucifer_team(ctx, item, team)
            continue
        try:
            tid = int(raw)
        except ValueError:
            continue
        _apply_lucifer_deceive(ctx, item, tid)


def _apply_lucifer_team(
    ctx: dict[str, Any],
    luci: dict[str, Any],
    team: str,
) -> None:
    """Map selected team code onto lucifer."""
    map_team = {
        "rosta": "villager",
        "wolf": "wolf",
        "ferqeTeem": "cult",
        "vampire": "solo",
        "qatel": "solo",
    }
    luci["team"] = map_team.get(team, "villager")
    ctx["flags_out"]["lucifer_team"] = team
    ctx["messages"].append("LuciferTeamSet")


def _apply_lucifer_deceive(
    ctx: dict[str, Any],
    luci: dict[str, Any],
    tid: int,
) -> None:
    """Death chances + day/vote/night steal flags."""
    target = player(ctx, tid)
    if target is None:
        ctx["messages"].append("DodgeDeadPlayer")
        return
    role = str(target.get("role") or "")
    rng = SystemRandom()
    uid = int(luci["user_id"])
    # PHP: if chance < R(100) → lucifer dies
    if role == "role_Alpha":
        ctx["deaths"].add(uid)
        ctx["messages"].append("LuciferEaten")
        return
    if role == "role_shekar":
        ctx["messages"].append("LuciferBlockedHunter")
        return
    if role == "role_Qatel":
        if _chance("dodge_qatel_dead") < rng.randrange(
            100
        ):
            ctx["deaths"].add(uid)
            return
    if target.get("team") == "wolf" and role != (
        "role_Alpha"
    ):
        if _chance("dodge_wolf_dead") < rng.randrange(100):
            ctx["deaths"].add(uid)
            return
    if role == "role_Bloodthirsty":
        if _chance("dodge_blood_dead") < rng.randrange(
            100
        ):
            ctx["deaths"].add(uid)
            return
    if role in _DAY_STEAL:
        ctx["flags_out"][f"dodge_day:{tid}"] = str(uid)
        ctx["messages"].append("LuciferDodgeDay")
        return
    if role in _NIGHT_STEAL:
        # Steal: clear victim night action
        ctx["actions"].pop(str(tid), None)
        ctx["flags_out"][f"dodge_night:{tid}"] = str(uid)
        ctx["messages"].append("LuciferDodgeNight")
        return
    ctx["flags_out"][f"dodge_vote:{tid}"] = str(uid)
    ctx["messages"].append("LuciferDodgeVote")



async def resolve_dynamite_night(
    ctx: dict[str, Any],
) -> None:
    """Night search for bomb parts."""
    parts = set(ctx.get("bomber_parts") or [])
    finds = int(ctx.get("dinamit_finds") or 0)
    for item in ctx["players"]:
        if item.get("role") not in {
            "role_dynamite",
            "role_dinamit",
        }:
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        if tid in parts:
            parts.discard(tid)
            finds += 1
            ctx.setdefault("seer_notes", []).append(
                (
                    int(item["user_id"]),
                    "",
                    "DinamitFindPart",
                )
            )
            ctx["messages"].append("DinamitFind")
        else:
            ctx.setdefault("seer_notes", []).append(
                (
                    int(item["user_id"]),
                    "",
                    "DinamitMiss",
                )
            )
    ctx["bomber_parts"] = parts
    ctx["dinamit_finds"] = finds
    ctx["flags_out"]["dinamit_finds"] = str(finds)
    if parts:
        ctx["flags_out"]["bomber_parts"] = json.dumps(
            sorted(int(x) for x in parts)
        )


def alive_targets_hide_bride(
    players: list[dict[str, Any]],
    actor_id: int,
) -> list[tuple[int, str]]:
    """Targets excluding self and Bride."""
    out: list[tuple[int, str]] = []
    for p in players:
        if not p.get("alive", True):
            continue
        uid = int(p["user_id"])
        if uid == actor_id:
            continue
        if p.get("role") == "role_BrideTheDead":
            continue
        out.append((uid, str(p["fullname"])))
    return out
