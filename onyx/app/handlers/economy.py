"""Wallet-only economy for Telegram bot (shop→webapp)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.cache.redis_client import get_redis
from app.handlers import deps
from app.managers.lobby_coins import (
    add_coins,
    deduct_coins,
    get_user_coins,
)


_DISABLED = (
    "EconomyMovedToWebapp"
)


async def mycoin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show user coin balance."""
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    bal = await get_user_coins(user.id)
    text = tm.get(
        "MyCoinBalance",
        lang,
        bal,
        bundle="lobby",
    )
    await context.bot.send_message(
        chat_id=chat.id,
        text=text,
    )


async def sendcoin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Transfer coins to replied user (min 4)."""
    user = update.effective_user
    chat = update.effective_chat
    msg = update.effective_message
    if user is None or chat is None or msg is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    reply = msg.reply_to_message
    if reply is None or reply.from_user is None:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "SendCoinNeedReply",
                lang,
                bundle="lobby",
            ),
        )
        return
    target = reply.from_user
    if target.is_bot or target.id == user.id:
        return
    args = context.args or []
    try:
        amount = int(args[0]) if args else 0
    except ValueError:
        amount = 0
    if amount < 4:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "SendCoinMinFour",
                lang,
                bundle="lobby",
            ),
        )
        return
    if not await _under_daily_cap(user.id, amount):
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "SendCoinDailyCap",
                lang,
                bundle="lobby",
            ),
        )
        return
    bal = await get_user_coins(user.id)
    if bal <= 0:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "NotValidateSendCoin",
                lang,
                bundle="main",
            ),
        )
        return
    if bal < amount:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "NotValidateSendCoinCredit",
                lang,
                bundle="main",
            ),
        )
        return
    if not await deduct_coins(user.id, amount):
        return
    await add_coins(target.id, amount)
    await _bump_daily(user.id, amount)
    await context.bot.send_message(
        chat_id=chat.id,
        text=tm.get(
            "SendCoinOk",
            lang,
            amount,
            target.full_name,
            bundle="lobby",
        ),
    )


async def shop_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Shop deferred to webapp — no dead UI."""
    await _disabled(update, context)


async def coin_pack_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Paid packs cut until bank gateway (MF-37…39)."""
    await _disabled(update, context)


async def _disabled(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    await context.bot.send_message(
        chat_id=chat.id,
        text=tm.get(
            _DISABLED,
            lang,
            bundle="lobby",
        ),
    )


async def _under_daily_cap(
    user_id: int,
    amount: int,
) -> bool:
    """Max 5 sendcoin transfers per UTC day."""
    redis = await get_redis()
    key = f"sendcoin_day:{user_id}"
    raw = await redis.get(key)
    used = int(raw or "0")
    return used < 5


async def _bump_daily(
    user_id: int,
    amount: int,
) -> None:
    """Increment daily sendcoin counter."""
    _ = amount
    redis = await get_redis()
    key = f"sendcoin_day:{user_id}"
    n = int(await redis.get(key) or "0") + 1
    await redis.set(key, str(n))
    await redis.expire(key, 86400)
