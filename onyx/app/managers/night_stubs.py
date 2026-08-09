"""Sprint-01 stub night slots (order-preserving)."""

from __future__ import annotations

from typing import Any


class NightStubs:
    """No-op / minimal slots so CheckNight order holds."""

    async def forest_queen_curse(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: DeadforestQueen empty-home."""
        _ = ctx

    async def check_harley(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: Harley after joker death."""
        _ = ctx

    async def check_knight(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: knight night action."""
        _ = ctx

    async def check_beta_wolf(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: beta wolf."""
        _ = ctx

    async def check_babr(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: babr."""
        _ = ctx

    async def check_ice_wolf(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Prefer: set PlayerIced flag from action."""
        for item in ctx["players"]:
            if item.get("role") != "role_IceWolf":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                ctx["flags_out"]["player_iced"] = str(raw)

    async def check_chemist(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: chemist."""
        _ = ctx

    async def check_bomber(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: bomber."""
        _ = ctx

    async def check_firefighter(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: firefighter."""
        _ = ctx

    async def check_magento(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: magento."""
        _ = ctx

    async def check_archer(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: archer."""
        _ = ctx

    async def check_chiang(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: chiang."""
        _ = ctx

    async def check_vampire(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Vampire bite → VampireBitten if convert key."""
        from random import SystemRandom

        key = ctx.get("vampire_convert")
        if not key:
            return
        try:
            chance = int(key)
        except (TypeError, ValueError):
            chance = 40
        for item in ctx["players"]:
            if item.get("role") != "role_vampire":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if not raw:
                continue
            if SystemRandom().randrange(100) >= chance:
                return
            ctx["flags_out"]["convert_vampire"] = str(raw)
            ctx["messages"].append("PlayerBitten")
            return

    async def lucifer_team(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: lucifer team."""
        _ = ctx

    async def check_bride(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: bride of the dead."""
        _ = ctx

    async def check_ice_queen(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: ice queen."""
        _ = ctx

    async def check_lilis(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: lilis."""
        _ = ctx

    async def check_honey(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Set HoneyUser from action if role present."""
        for item in ctx["players"]:
            if item.get("role") != "role_Honey":
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                ctx["flags_out"]["honey_user"] = str(raw)

    async def check_kent(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: kent."""
        _ = ctx

    async def check_franc(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Franc house guard selection → defense set."""
        guards: set[str] = set(ctx.get("franc_guard") or [])
        for item in ctx["players"]:
            if item.get("role") != "role_Franc":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                guards.add(str(raw))
        ctx["franc_guard"] = guards

    async def check_enchanter(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Prefer: store enchanter list for bites."""
        for item in ctx["players"]:
            if item.get("role") != "role_Enchanter":
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                ctx["flags_out"]["enchanter_mark"] = str(
                    raw
                )

    async def check_cow(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: cow."""
        _ = ctx

    async def check_huntsman(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Huntsman trap target for wolf defense."""
        for item in ctx["players"]:
            if item.get("role") != "role_Huntsman":
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                ctx["huntsman_trap"] = int(raw)

    async def check_ghost(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: ghost."""
        _ = ctx

    async def check_mouse(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: mouse."""
        _ = ctx

    async def check_white_wolf(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: white wolf solo path handled in team."""
        _ = ctx

    async def check_augur(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: augur."""
        _ = ctx

    async def check_phoenix(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Prefer: PhoenixHealer on night 2/4."""
        night = int(ctx.get("night_no") or 0)
        if night not in {2, 4}:
            return
        heals: set[int] = set(ctx.get("phoenix_heals") or [])
        for item in ctx["players"]:
            if item.get("role") != "role_Phoenix":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                heals.add(int(raw))
                ctx["flags_out"]["phoenix_healer"] = str(
                    raw
                )
        ctx["phoenix_heals"] = heals

    async def check_thief(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: thief."""
        _ = ctx

    async def check_negative(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: negative / monafeq."""
        _ = ctx

    async def check_sorcerer(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: sorcerer."""
        _ = ctx

    async def check_dynamite(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: dynamite."""
        _ = ctx

    async def check_watermelon(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: watermelon."""
        _ = ctx

    async def check_bard(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: bard / khenyager."""
        _ = ctx
