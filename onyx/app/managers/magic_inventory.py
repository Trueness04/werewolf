"""Magic inventory: shop IDs ↔ in-game effect types."""

from __future__ import annotations

from sqlalchemy import select

from app.database.models.social import ShopOwnedRow
from app.database.session import session_scope

# Web shop id → keyboard / PHP effect type
SHOP_TO_EFFECT: dict[str, str] = {
    "MajikReveal": "MajiKhabar",
    "MajikProtect": "MajiKHil",
    "MajikSilence": "MajiKGhost",
    "MajikSear": "MajikSear",
    "MajiKhabar": "MajiKhabar",
    "MajiKHil": "MajiKHil",
    "MajiKGhost": "MajiKGhost",
}

EFFECT_TO_SHOP: dict[str, str] = {
    "MajiKhabar": "MajikReveal",
    "MajiKHil": "MajikProtect",
    "MajiKGhost": "MajikSilence",
    "MajikSear": "MajikSear",
}

EFFECT_TYPES: tuple[str, ...] = (
    "MajiKhabar",
    "MajikSear",
    "MajiKHil",
    "MajiKGhost",
)


async def inventory_counts(user_id: int) -> dict[str, int]:
    """Effect-type → qty from ShopOwnedRow (mapped)."""
    counts = {t: 0 for t in EFFECT_TYPES}
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(ShopOwnedRow).where(
                    ShopOwnedRow.user_id == user_id
                )
            )
        ).scalars().all()
        for row in rows:
            effect = SHOP_TO_EFFECT.get(str(row.item_id))
            if effect is None:
                continue
            counts[effect] = counts.get(effect, 0) + int(
                row.qty
            )
    return counts


async def total_magic(user_id: int) -> int:
    """Sum of all magic qty."""
    return sum((await inventory_counts(user_id)).values())


async def consume_effect(
    user_id: int,
    effect_type: str,
    *,
    qty: int = 1,
) -> bool:
    """Decrement shop row for mapped item; False if none."""
    shop_id = EFFECT_TO_SHOP.get(effect_type)
    if shop_id is None:
        return False
    async with session_scope() as session:
        # Prefer web shop id; fall back to effect id row
        for item_id in (shop_id, effect_type):
            row = (
                await session.execute(
                    select(ShopOwnedRow).where(
                        ShopOwnedRow.user_id == user_id,
                        ShopOwnedRow.item_id == item_id,
                    )
                )
            ).scalar_one_or_none()
            if row is None or int(row.qty) < qty:
                continue
            row.qty = int(row.qty) - qty
            if row.qty <= 0:
                session.delete(row)
            return True
    return False


async def refund_effect(
    user_id: int,
    effect_type: str,
    *,
    qty: int = 1,
) -> None:
    """Return magic to inventory (death refund)."""
    shop_id = EFFECT_TO_SHOP.get(effect_type, effect_type)
    async with session_scope() as session:
        row = (
            await session.execute(
                select(ShopOwnedRow).where(
                    ShopOwnedRow.user_id == user_id,
                    ShopOwnedRow.item_id == shop_id,
                )
            )
        ).scalar_one_or_none()
        if row:
            row.qty = int(row.qty) + qty
        else:
            session.add(
                ShopOwnedRow(
                    user_id=user_id,
                    item_id=shop_id,
                    qty=qty,
                )
            )
