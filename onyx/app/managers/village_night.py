"""Sprint 05f village night resolvers."""

from __future__ import annotations

from random import SystemRandom
from typing import Any

from app.config.paths import CONFIG_DATA
from app.managers.json_loader import load_json
from app.managers.night_village import player

_CFG = CONFIG_DATA / "village_chances.json"


def _cfg() -> dict[str, Any]:
    return load_json(_CFG)


async def resolve_knight(ctx: dict[str, Any]) -> None:
    """Village knight night kill (early slot)."""
    cfg = _cfg()
    rng = SystemRandom()
    for item in ctx["players"]:
        if item.get("role") != "role_Knight":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        kid = int(item["user_id"])
        tid = int(raw)
        target = player(ctx, tid)
        if target is None or not target.get("alive", True):
            ctx["messages"].append("KnightPlayerIsDeadSee")
            continue
        trap = ctx.get("huntsman_trap")
        if trap is not None and int(trap) == tid:
            if rng.randrange(100) < 50:
                ctx["deaths"].add(kid)
                ctx["messages"].append("HuntsmanKill")
                continue
        heals = ctx.get("phoenix_heals") or set()
        if tid in heals:
            ctx["messages"].append("MessageForKnight")
            continue
        role = str(target.get("role") or "")
        if role == "role_qhost":
            ctx["find_ghost"] = True
            ctx.setdefault("flags_out", {})[
                "find_ghost"
            ] = "1"
            ctx["messages"].append("GhostFinde")
        if role == "role_BlackKnight":
            ctx["deaths"].add(kid)
            ctx["messages"].append("BlackKnightKillKnight")
            continue
        if role == "role_betaWolf":
            ctx["deaths"].add(kid)
            ctx["deaths"].add(tid)
            ctx["messages"].append("betaWolf_knight")
            continue
        if role == "role_Lilis":
            if rng.randrange(100) < int(
                cfg["knight_vs_lilis"]
            ):
                ctx["deaths"].add(kid)
            else:
                ctx["deaths"].add(tid)
            continue
        if role in set(cfg["knight_kill_roles"]):
            ctx["deaths"].add(tid)
            ctx["messages"].append("KnightKill")
            continue
        ctx["messages"].append("KnightNoKillUser")


async def resolve_chemist(ctx: dict[str, Any]) -> None:
    """Chemist 50/50 poison; risky vs SK."""
    cfg = _cfg()
    rng = SystemRandom()
    for item in ctx["players"]:
        if item.get("role") != "role_Chemist":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        cid = int(item["user_id"])
        tid = int(raw)
        target = player(ctx, tid)
        if target is None or not target.get("alive", True):
            ctx["messages"].append("ChemistTargetDead")
            continue
        role = str(target.get("role") or "")
        if role == "role_Qatel":
            if rng.randrange(100) < int(
                cfg["chemist_vs_sk"]
            ):
                ctx["deaths"].add(cid)
                ctx["messages"].append("ChemistSK")
                continue
        if role == "role_rishSefid":
            # Elder shot → chemist becomes villager
            item["role"] = "role_villager"
            item["team"] = "villager"
            ctx["roles"][str(cid)] = "role_villager"
            ctx["deaths"].add(tid)
            ctx["messages"].append("ChemistElder")
            continue
        if rng.randrange(100) < int(cfg["chemist_success"]):
            ctx["deaths"].add(tid)
            ctx["messages"].append("ChemistSuccess")
        else:
            ctx["deaths"].add(cid)
            ctx["messages"].append("ChemistFail")


async def resolve_cow(ctx: dict[str, Any]) -> None:
    """Cow night gore — kill non-wolf or die on wolf."""
    for item in ctx["players"]:
        if item.get("role") != "role_Cow":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        target = player(ctx, tid)
        if target is None or not target.get("alive", True):
            continue
        guards = set(ctx.get("franc_guard") or set())
        heals = ctx.get("phoenix_heals") or set()
        if str(tid) in guards or tid in heals:
            ctx["messages"].append("CowAngel")
            continue
        if target.get("team") == "wolf":
            ctx["deaths"].add(int(item["user_id"]))
            ctx["messages"].append("CowVsWolf")
        else:
            ctx["deaths"].add(tid)
            ctx["messages"].append("GroupMesageCowKill")


async def resolve_ghost(ctx: dict[str, Any]) -> None:
    """Ghost night peek until FindGhost."""
    if ctx.get("find_ghost"):
        return
    for item in ctx["players"]:
        if item.get("role") != "role_qhost":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        role_id = str(ctx["roles"].get(str(tid), ""))
        ctx.setdefault("seer_notes", []).append(
            (int(item["user_id"]), role_id, "ghostSee")
        )


async def resolve_mouse(ctx: dict[str, Any]) -> None:
    """Mouse detects enemy presence."""
    enemies = set(_cfg()["mouse_enemy_roles"])
    for item in ctx["players"]:
        if item.get("role") != "role_Mouse":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        trap = ctx.get("huntsman_trap")
        if trap is not None and int(trap) == tid:
            if SystemRandom().randrange(100) < 50:
                ctx["deaths"].add(int(item["user_id"]))
                continue
        role = str(ctx["roles"].get(str(tid), ""))
        key = (
            "MouseInD" if role in enemies else "MouseInNotD"
        )
        ctx["messages"].append(key)


async def resolve_augur(ctx: dict[str, Any]) -> None:
    """Augur sees a missing-from-alive mode role."""
    alive_roles = {
        str(p.get("role") or "")
        for p in ctx["players"]
        if p.get("alive", True)
    }
    pool = [
        str(r)
        for r in ctx.get("mode_roles") or ctx["roles"].values()
        if r and str(r) not in alive_roles
    ]
    if not pool:
        # fallback: any known role not alive
        pool = [
            str(r)
            for r in set(ctx["roles"].values())
            if r and str(r) not in alive_roles
        ]
    for item in ctx["players"]:
        if item.get("role") != "role_Augur":
            continue
        if not item.get("alive", True):
            continue
        uid = int(item["user_id"])
        if not pool:
            ctx.setdefault("seer_notes", []).append(
                (uid, "", "AugurSeesNothing")
            )
            continue
        pick = SystemRandom().choice(pool[:3] or pool)
        ctx.setdefault("seer_notes", []).append(
            (uid, pick, "AugurSees")
        )


async def resolve_negative(ctx: dict[str, Any]) -> None:
    """Negative: random other role labeled as target."""
    for item in ctx["players"]:
        if item.get("role") != "role_ngativ":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        pool = [
            str(r)
            for uid, r in ctx["roles"].items()
            if r
            and int(uid) not in {int(item["user_id"]), tid}
        ]
        if not pool:
            ctx.setdefault("seer_notes", []).append(
                (int(item["user_id"]), "", "No_role")
            )
            continue
        fake = SystemRandom().choice(pool)
        ctx.setdefault("seer_notes", []).append(
            (int(item["user_id"]), fake, "NegSeerSees")
        )


async def deliver_seer_notes(
    ctx: dict[str, Any],
    bridge: Any,
    texts: Any,
    lang: str,
    label_fn: Any,
) -> None:
    """DM queued investigation notes."""
    for note in ctx.get("seer_notes") or []:
        if len(note) < 3:
            continue
        uid, role_id, key = note[0], note[1], note[2]
        if key in {
            "AugurSeesNothing",
            "No_role",
            "WatermelonChoseSuccess",
            "WatermelonChoseUser",
            "HildaSkDead",
            "VampireDrink",
            "DinamitFindPart",
            "DinamitMiss",
            "PlayerDead",
        }:
            await bridge.send_text(
                int(uid),
                texts.get(key, lang, bundle="results"),
            )
            continue
        label = label_fn(str(role_id)) if role_id else ""
        await bridge.send_text(
            int(uid),
            texts.get(key, lang, label, bundle="results"),
        )
