"""ChangeConfig-style role toggle pair sync."""

from __future__ import annotations

from copy import deepcopy


def sync_role_toggles(
    toggles: dict[str, bool],
) -> dict[str, bool]:
    """Return toggles with sprint-3 pair rules applied.

    Keys use role_id without role_ prefix optional;
    both forms accepted for vamp/blood.
    """
    t = deepcopy(toggles)

    def get(key: str) -> bool:
        return bool(t.get(key, t.get(f"role_{key}", False)))

    def set_(key: str, value: bool) -> None:
        if key in t:
            t[key] = value
        alt = f"role_{key}" if not key.startswith("role_") else key[5:]
        if alt in t:
            t[alt] = value
        t[key] = value

    # Vampire ↔ Bloodthirsty always equal
    vamp = get("vampire") or get("role_vampire")
    blood = get("bloodthirsty") or get(
        "role_Bloodthirsty"
    )
    if vamp != blood:
        # Last write wins: prefer vampire key if set
        both = vamp or blood
        set_("vampire", both)
        set_("bloodthirsty", both)
        set_("role_vampire", both)
        set_("role_Bloodthirsty", both)
    # kalantar off → both vamp off
    if not get("kalantar") and "kalantar" in t:
        set_("vampire", False)
        set_("bloodthirsty", False)
        set_("role_vampire", False)
        set_("role_Bloodthirsty", False)
    # ferqe ↔ shekar ↔ Royce
    if get("Royce") or get("role_Royce"):
        set_("ferqe", True)
        set_("shekar", True)
        set_("role_ferqe", True)
        set_("role_shekar", True)
    if get("ferqe") or get("role_ferqe"):
        set_("shekar", True)
        set_("role_shekar", True)
    if get("shekar") or get("role_shekar"):
        set_("ferqe", True)
        set_("role_ferqe", True)
    # IceQueen ↔ Firefighter
    ice = get("IceQueen") or get("role_IceQueen")
    fire = get("firefighter") or get(
        "role_firefighter"
    )
    if ice != fire:
        both = ice or fire
        set_("IceQueen", both)
        set_("firefighter", both)
        set_("role_IceQueen", both)
        set_("role_firefighter", both)
    # Qatel off → Archer off; Archer on → Qatel on
    if not get("Qatel") and "Qatel" in t:
        set_("Archer", False)
        set_("role_Archer", False)
    if get("Archer") or get("role_Archer"):
        set_("Qatel", True)
        set_("role_Qatel", True)
    return t


def has_base_wolf(roles: list[str], bases: list[str]) -> bool:
    """True if pool has at least one base wolf."""
    return any(r in bases for r in roles)
