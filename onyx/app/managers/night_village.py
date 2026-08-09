"""Village night helpers (elder/mast/natasha/...)."""

from __future__ import annotations

from typing import Any

from app.managers.chat_bridge import ChatBridge
from app.managers.text_managers import TextManager
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


def player(
    ctx: dict[str, Any],
    user_id: int,
) -> dict[str, Any] | None:
    """Find player dict by user id."""
    for item in ctx["players"]:
        if int(item["user_id"]) == user_id:
            return item
    return None


class NightVillage:
    """Village-side night resolution helpers."""

    def __init__(
        self,
        bridge: ChatBridge,
        texts: TextManager,
        lang: str,
    ) -> None:
        self._bridge = bridge
        self._texts = texts
        self._lang = lang
        self._registry = _Registry()

    def seer_label(self, role_id: str) -> str:
        """Masked role label for seer / fool."""
        if not role_id:
            return ""
        if role_id in {"role_Khaen", "role_NefrinShode"}:
            role_id = "role_Shahzade"
        if role_id == "role_WhiteWolf":
            role_id = "role_wolf"
        mk = self._registry.definition(role_id)[
            "message_keys"
        ]["name"]
        return self._texts.get(
            str(mk),
            self._lang,
            bundle="roles",
        )

    async def dm_role_result(
        self,
        actor: int,
        label: str,
    ) -> None:
        """Send private investigation result."""
        text = self._texts.get(
            "user_role",
            self._lang,
            label,
            bundle="results",
        )
        await self._bridge.send_text(actor, text)

    async def cult_hunter(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Kill cultist / die on SK / noop else."""
        for item in ctx["players"]:
            if item.get("role") != "role_shekar":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if not raw:
                continue
            tid = int(raw)
            target = player(ctx, tid)
            if target is None:
                continue
            team = str(target.get("team") or "")
            role = str(target.get("role") or "")
            if team == "cult" or role == "role_ferqe":
                ctx["deaths"].add(tid)
                ctx["messages"].append(
                    self._texts.get(
                        "CultHunterKilled",
                        self._lang,
                        str(target["fullname"]),
                        bundle="results",
                    )
                )
            elif role == "role_Qatel":
                ctx["deaths"].add(int(item["user_id"]))

    async def natasha_visit(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Visit home; die on wolf/SK; track host."""
        for item in ctx["players"]:
            if item.get("role") != "role_Natasha":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if not raw:
                continue
            host_id = int(raw)
            ctx["natasha_host"] = host_id
            ctx["natasha_id"] = int(item["user_id"])
            host = player(ctx, host_id)
            if host is None:
                continue
            role = str(host.get("role") or "")
            team = str(host.get("team") or "")
            if team == "wolf" or role == "role_Qatel":
                ctx["deaths"].add(int(item["user_id"]))
                ctx["messages"].append(
                    self._texts.get(
                        "NatashaDiedVisit",
                        self._lang,
                        str(item["fullname"]),
                        bundle="results",
                    )
                )

    def apply_empty_home(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Wolf/SK miss if target is Natasha away."""
        natasha = ctx.get("natasha_id")
        if natasha is None:
            return
        for key in ("wolf_target", "sk_target"):
            if ctx.get(key) == natasha:
                ctx[key] = None
                ctx["messages"].append(
                    self._texts.get(
                        "EmptyHome",
                        self._lang,
                        bundle="results",
                    )
                )

    def follow_natasha_death(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """If host dies, Natasha dies with them."""
        host = ctx.get("natasha_host")
        natasha = ctx.get("natasha_id")
        if host is None or natasha is None:
            return
        if int(host) in ctx["deaths"]:
            ctx["deaths"].add(int(natasha))

    def wild_child_pick(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Store model id chosen by wild child."""
        for item in ctx["players"]:
            if item.get("role") != "role_Vahshi":
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                ctx["flags_out"]["wild_child_model"] = (
                    str(int(raw))
                )
                ctx["flags_out"][
                    "wild_child_id"
                ] = str(item["user_id"])

    def convert_wild_child(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Model death → wild child becomes wolf."""
        model = ctx.get("wild_child_model")
        child = ctx.get("wild_child_id")
        if not model or not child:
            return
        mid = int(model)
        cid = int(child)
        if mid not in ctx["deaths"]:
            return
        item = player(ctx, cid)
        if item is None or not item.get("alive", True):
            return
        if cid in ctx["deaths"]:
            return
        item["role"] = "role_wolf"
        item["team"] = "wolf"
        ctx["roles"][str(cid)] = "role_wolf"
        ctx["messages"].append(
            self._texts.get(
                "OlgoChangedTo",
                self._lang,
                str(item["fullname"]),
                bundle="results",
            )
        )

    def promote_apprentice(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Seer death → apprentice becomes seer."""
        seer_dead = False
        for uid in list(ctx["deaths"]):
            item = player(ctx, int(uid))
            if item and item.get("role") == "role_pishgo":
                seer_dead = True
                break
        if not seer_dead:
            return
        for item in ctx["players"]:
            if item.get("role") != "role_pishRezerv":
                continue
            if not item.get("alive", True):
                continue
            if int(item["user_id"]) in ctx["deaths"]:
                continue
            item["role"] = "role_pishgo"
            ctx["roles"][str(item["user_id"])] = (
                "role_pishgo"
            )
            ctx["messages"].append(
                self._texts.get(
                    "ApprenticeNowSeer",
                    self._lang,
                    str(item["fullname"]),
                    bundle="results",
                )
            )
            return

    def guardian_dies_on_evil(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Angel dies if visiting wolf or SK home."""
        protected = ctx.get("protected")
        if protected is None:
            return
        host = player(ctx, int(protected))
        if host is None:
            return
        role = str(host.get("role") or "")
        team = str(host.get("team") or "")
        if team != "wolf" and role != "role_Qatel":
            return
        for item in ctx["players"]:
            if item.get("role") != "role_Fereshte":
                continue
            if not item.get("alive", True):
                continue
            ctx["deaths"].add(int(item["user_id"]))
