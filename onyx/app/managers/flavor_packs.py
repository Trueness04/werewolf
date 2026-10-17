"""Flavor (tone) pack helpers from flavor_packs.json."""

from __future__ import annotations

from app.config.paths import FLAVOR_PACKS
from app.managers.json_loader import load_json


def load_flavor_packs() -> dict[str, dict]:
    """Return enabled pack id → meta."""
    raw = load_json(FLAVOR_PACKS)
    packs = raw.get("packs", {})
    out: dict[str, dict] = {}
    for pack_id, meta in packs.items():
        if not bool(meta.get("enabled", True)):
            continue
        out[str(pack_id)] = {
            "display_key": str(
                meta.get("display_key", pack_id)
            ),
            "catalog": str(
                meta.get("catalog", pack_id)
            ),
        }
    return out


def default_flavor_pack() -> str:
    """Default pack id from config."""
    raw = load_json(FLAVOR_PACKS)
    return str(raw.get("default", "general"))


def resolve_catalog(pack_id: str | None) -> str:
    """Map pack id to TextManager catalog file."""
    if not pack_id:
        return "general"
    packs = load_flavor_packs()
    meta = packs.get(str(pack_id))
    if meta is None:
        return "general"
    catalog = str(meta["catalog"])
    if catalog == "general":
        return "general"
    return catalog


def is_known_pack(pack_id: str) -> bool:
    """True when pack id is enabled in config."""
    return str(pack_id) in load_flavor_packs()
