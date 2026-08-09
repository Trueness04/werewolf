"""Wolf + SK role-branch outcomes after defenses."""

from __future__ import annotations

from random import SystemRandom
from typing import Any

from app.config.paths import ROOT
from app.managers.json_loader import load_json
from app.managers.night_attack import angel_target
from app.managers.night_village import player

_CHANCES = ROOT / "data" / "config" / "field_chances.json"


def _chance(key: str) -> int:
    """Read percent chance from config."""
    return int(load_json(_CHANCES)[key])


def _blood_hidden(ctx: dict[str, Any]) -> bool:
    """True if Bloodthirsty not yet revealed."""
    return not bool(
        ctx.get("blood_revealed")
        or (ctx.get("flags") or {}).get("blood_revealed")
    )


def wolf_role_branch(
    ctx: dict[str, Any],
    target_id: int,
) -> str:
    """Return blocked|bitten|eaten|elder|mast."""
    victim = player(ctx, target_id)
    if victim is None:
        return "blocked"
    role = str(victim.get("role") or "")
    rng = SystemRandom()
    if role == "role_NefrinShode":
        victim["role"] = "role_wolf"
        victim["team"] = "wolf"
        ctx["roles"][str(target_id)] = "role_wolf"
        ctx["messages"].append("eat_nefrin")
        return "blocked"
    if role == "role_rishSefid" and not ctx.get(
        "elder_used"
    ):
        ctx["flags_out"]["elder_saved"] = "1"
        ctx["messages"].append("EatRishSefid")
        return "elder"
    if role == "role_Mast":
        ctx["flags_out"]["mast_block_next"] = "1"
        ctx["deaths"].add(target_id)
        ctx["messages"].append("mastEatWolfGR")
        return "mast"
    if role == "role_Qatel":
        if rng.randrange(100) < _chance(
            "sk_vs_wolf_kill_chance"
        ):
            last = ctx.get("last_wolf_voter")
            if last is not None:
                ctx["deaths"].add(int(last))
            return "blocked"
    if role == "role_BlackKnight":
        last = ctx.get("last_wolf_voter")
        if last is not None and rng.randrange(100) < 50:
            ctx["deaths"].add(int(last))
            return "blocked"
        ctx["deaths"].add(target_id)
        return "eaten"
    if role == "role_joker":
        from app.managers.joker_books import (
            check_attack_joker,
        )

        if check_attack_joker(
            ctx,
            target_id,
            attacker_id=ctx.get("last_wolf_voter"),
            team_attack=True,
        ):
            return "blocked"
    if role == "role_kalantar":
        wolves = sum(
            1
            for p in ctx["players"]
            if p.get("team") == "wolf"
            and p.get("alive", True)
        )
        chance = _chance("hunter_kill_wolf_base") + (
            max(wolves - 1, 0)
            * _chance("hunter_kill_wolf_per_extra")
        )
        if rng.randrange(100) < chance:
            ctx["flags_out"]["hunter_kill"] = str(
                target_id
            )
            ctx["stop_night"] = True
            ctx["deaths"].add(target_id)
            return "eaten"
    protected = angel_target(ctx)
    if protected == target_id:
        ctx["messages"].append("GuardSaved")
        return "blocked"
    from app.managers.village_links import (
        apply_sweetheart_love,
    )

    if (
        victim.get("role") == "role_Sweetheart"
        and ctx.get("last_wolf_voter")
    ):
        if apply_sweetheart_love(
            ctx,
            int(ctx["last_wolf_voter"]),
            "wolf",
        ):
            return "blocked"
    if (
        victim.get("role") == "role_Bloodthirsty"
        and _blood_hidden(ctx)
    ):
        ctx["messages"].append("EmptyHome")
        return "blocked"
    if victim.get("role") == "role_Lilis":
        if rng.randrange(100) < _chance(
            "lilis_block_chance"
        ):
            last = ctx.get("last_wolf_voter")
            if last is not None:
                ctx["deaths"].add(int(last))
            return "blocked"
    marked_ids = {
        str(x)
        for x in (ctx.get("enchanter_list") or [])
    }
    mark = str(
        ctx.get("enchanter_mark")
        or (ctx.get("flags") or {}).get("enchanter_mark")
        or ""
    )
    if mark:
        marked_ids.add(mark)
    if str(target_id) in marked_ids:
        if rng.randrange(100) < _chance(
            "enchanter_convert"
        ):
            ctx["flags_out"]["convert_enchanter"] = str(
                target_id
            )
            ctx["messages"].append("PlayerBitten")
            return "bitten"
    alpha_dead = bool(
        ctx.get("alpha_dead")
        or (ctx.get("flags") or {}).get("alpha_dead")
    )
    if alpha_dead:
        if rng.randrange(100) < _chance(
            "forest_queen_convert"
        ):
            ctx["flags_out"]["convert_wolf"] = str(
                target_id
            )
            ctx["messages"].append("PlayerBitten")
            return "bitten"
    if rng.randrange(100) < _chance("alpha_convert"):
        ctx["flags_out"]["convert_wolf"] = str(target_id)
        ctx["flags_out"]["dozd_alpha_hit"] = "1"
        ctx["messages"].append("PlayerBitten")
        return "bitten"
    ctx["deaths"].add(target_id)
    return "eaten"


def killer_role_branch(
    ctx: dict[str, Any],
    target_id: int,
) -> str:
    """SK role branch; return blocked|killed."""
    victim = player(ctx, target_id)
    if victim is None:
        return "blocked"
    role = str(victim.get("role") or "")
    if role == "role_BlackKnight":
        for item in ctx["players"]:
            if item.get("role") == "role_Qatel":
                ctx["deaths"].add(int(item["user_id"]))
        return "blocked"
    if role == "role_joker":
        from app.managers.joker_books import (
            check_attack_joker,
        )

        sk_id = None
        for sk in ctx["players"]:
            if sk.get("role") == "role_Qatel":
                sk_id = int(sk["user_id"])
                break
        if check_attack_joker(
            ctx,
            target_id,
            attacker_id=sk_id,
            team_attack=False,
        ):
            return "blocked"
    protected = angel_target(ctx)
    if protected == target_id:
        ctx["messages"].append("GuardBlockedKiller")
        return "blocked"
    if victim.get("role") == "role_Sweetheart":
        from app.managers.village_links import (
            apply_sweetheart_love,
        )

        for sk in ctx["players"]:
            if sk.get("role") == "role_Qatel":
                if apply_sweetheart_love(
                    ctx,
                    int(sk["user_id"]),
                    "qatel",
                ):
                    return "blocked"
    if (
        victim.get("role") == "role_Bloodthirsty"
        and _blood_hidden(ctx)
    ):
        ctx["messages"].append("EmptyHome")
        return "blocked"
    if victim.get("role") == "role_Lilis":
        if SystemRandom().randrange(100) < _chance(
            "lilis_block_chance"
        ):
            for sk in ctx["players"]:
                if sk.get("role") == "role_Qatel":
                    if sk.get("alive", True):
                        ctx["deaths"].add(
                            int(sk["user_id"])
                        )
            return "blocked"
    if role == "role_kalantar":
        ctx["flags_out"]["hunter_kill"] = str(target_id)
        ctx["stop_night"] = True
    ctx["deaths"].add(target_id)
    return "killed"
