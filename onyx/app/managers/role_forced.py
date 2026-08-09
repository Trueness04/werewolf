"""Pre-balance forced role pair fixes (UserRole A–I)."""

from __future__ import annotations

from random import SystemRandom

from app.config.paths import CONFIG_DATA
from app.managers.json_loader import load_json
from app.managers.role_pairs import has_base_wolf

_RULES = CONFIG_DATA / "role_pair_rules.json"


def force_role_pairs(
    roles: list[str],
    rng: SystemRandom | None = None,
) -> list[str]:
    """Apply sprint-3 forced converts A–I on role list."""
    rng = rng or SystemRandom()
    rules = load_json(_RULES)
    bases = [str(x) for x in rules["base_wolves"]]
    deps = [str(x) for x in rules["wolf_dependents"]]
    out = list(roles)
    villager = str(rules["villager_inject"])
    non_vg = {
        str(x)
        for x in rules.get("non_vg", rules["no_inject"])
    }

    def count(rid: str) -> int:
        return sum(1 for r in out if r == rid)

    def replace_first(old: str, new: str) -> None:
        for i, r in enumerate(out):
            if r == old:
                out[i] = new
                return

    def inject(rid: str) -> bool:
        """Replace a random non-Vg slot (GetRandomvg fix)."""
        idxs = [
            i
            for i, r in enumerate(out)
            if r not in non_vg
        ]
        if not idxs:
            return False
        out[rng.choice(idxs)] = rid
        return True

    # A: wolf dependents without base wolf → base wolf
    if not has_base_wolf(out, bases):
        for dep in deps:
            if count(dep) > 0:
                replace_first(dep, rng.choice(bases))
    # Khaen without any wolf enemy → wolf
    if count("role_Khaen") and not has_base_wolf(
        out,
        bases,
    ):
        replace_first("role_Khaen", rng.choice(bases))
    # B: Archer without Qatel → Qatel
    if count("role_Archer") and not count("role_Qatel"):
        replace_first("role_Archer", "role_Qatel")
    # C: forestQueen without Alpha → Alpha
    if count("role_forestQueen") and not count(
        "role_Alpha"
    ):
        replace_first("role_forestQueen", "role_Alpha")
    # D–F: Vampire/Blood/kalantar incomplete
    if count("role_vampire") and not count(
        "role_kalantar"
    ):
        inject("role_kalantar")
    if count("role_Bloodthirsty") and not count(
        "role_vampire"
    ):
        inject("role_vampire")
    if count("role_vampire") and not count(
        "role_Bloodthirsty"
    ):
        inject("role_Bloodthirsty")
    # G–H: ferqe / Royce / DarNeshan without shekar
    if (
        count("role_ferqe")
        or count("role_Royce")
        or count("role_DarNeshan")
    ) and not count("role_shekar"):
        inject("role_shekar")
    if count("role_BeladMoon") and not count(
        "role_vampire"
    ):
        inject("role_vampire")
    # I: PishRezerv without pishgo → pishgo
    if count("role_pishRezerv") and not count(
        "role_pishgo"
    ):
        replace_first("role_pishRezerv", "role_pishgo")
    # Pair guards: drop incomplete pairs
    if bool(count("role_IceQueen")) ^ bool(
        count("role_firefighter")
    ):
        if count("role_IceQueen"):
            replace_first(
                "role_IceQueen",
                villager,
            )
        if count("role_firefighter"):
            replace_first(
                "role_firefighter",
                villager,
            )
    if bool(count("role_joker")) ^ bool(
        count("role_harley")
    ):
        if count("role_joker") and not count(
            "role_harley"
        ):
            inject("role_harley")
        if count("role_harley") and not count(
            "role_joker"
        ):
            inject("role_joker")
    # Black knight ↔ bride required
    if bool(count("role_BlackKnight")) ^ bool(
        count("role_BrideTheDead")
    ):
        if count("role_BlackKnight"):
            inject("role_BrideTheDead")
        if count("role_BrideTheDead"):
            inject("role_BlackKnight")
    if count("role_dian") and (
        not count("role_BlackKnight")
        or not count("role_BrideTheDead")
    ):
        replace_first("role_dian", villager)
    if count("role_shekar") and not count("role_pishgo"):
        # keep shekar; seer not mandatory with hunter
        pass
    if count("role_franc") and not count("role_ferqe"):
        replace_first("role_franc", villager)
    return out
