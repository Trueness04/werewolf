---
name: onyx-telegram-button-styling
description: >-
  Design polished, color-coded Telegram bot keyboards (start menu, lobby,
  settings panel) for Onyx using Telegram Bot API 9.4's button `style` field
  (danger/red, success/green, primary/blue) and optional custom emoji icons.
  Use this skill whenever the user asks to make a Telegram bot menu "shiny",
  "colorful", "polished", mentions keyboardButtonStyle, or asks which buttons
  should be green/red/blue. Decide button color by the semantic weight of the
  action (confirm vs cancel vs neutral), not decoratively.
---

# Onyx Telegram Colored Keyboard Design

## What this is
Telegram Bot API 9.4 (Feb 9, 2026) added a `style` field to both
`KeyboardButton` and `InlineKeyboardButton`. Value is one of:

| style     | color      | Telegram's stated intent          |
|-----------|------------|------------------------------------|
| `success` | green      | positive / confirming actions      |
| `danger`  | red        | destructive / irreversible actions |
| `primary` | blue       | main / default action               |
| *(omitted)* | app default | neutral / secondary actions       |

There's also an optional `icon_custom_emoji_id` for a small emoji icon before
the button text (requires the bot owner to have Telegram Premium or a
purchased extra username — treat it as a nice-to-have, not a dependency).

## How to assign colors — semantic rule, not decoration
Go button-by-button through the menu and classify by what happens if the
user taps it:

- **`success` (green)** — join/enter/confirm/start/accept actions: "ورود به روستا" (join lobby), "تایید", "شروع بازی", accepting an invite, "بله" in a yes/no prompt like آهنگر/خوابگزار.
- **`danger` (red)** — leaving, canceling, force-ending, banning, declining: "ترک بازی", "لغو بازی", `/forcestart` cancel path, "خیر" in a yes/no prompt where "no" ends an opportunity, admin ban/kick buttons.
- **`primary` (blue)** — the single main call-to-action of a screen when it isn't strictly "confirm" (e.g. the top-level `/start` menu's main "شروع بازی جدید" button, `/config` entry button).
- **no style (default)** — everything else: informational buttons, "لیست بازیکنان", pagination (prev/next), settings sub-menu navigation. Don't color buttons that aren't a meaningful decision point — over-coloring defeats the purpose of using color as a signal.

Only one button per screen should typically be `primary`; a screen can have several `success`/`danger` buttons if there are genuinely several confirm/cancel-type choices (e.g. a settings toggle row).

## Applying this in code (python-telegram-bot / PTB)
As of recent PTB releases, `InlineKeyboardButton` and `KeyboardButton` may or may not yet expose `style` as a first-class constructor argument depending on the installed version. Handle both cases:

```python
# If the installed python-telegram-bot version supports it natively:
InlineKeyboardButton(text=label, callback_data=cb, style="success")

# If not yet supported natively, fall back to passing it through
# the underlying Bot API payload via api_kwargs on the send call,
# NOT by hand-building raw dicts inside handlers:
await bot.send_message(
    chat_id=chat_id,
    text=text,
    reply_markup=keyboard,
    api_kwargs={"reply_markup": {"inline_keyboard": [[
        {"text": label, "callback_data": cb, "style": "success"}
    ]]}},
)
```
Prefer the native argument when available; only use the `api_kwargs` escape hatch if the pinned PTB version in `requirements.txt` predates support. Check the installed version before assuming either path — don't guess.

## Zero-hardcoding rule still applies
Per Onyx's project rules: button **text** still comes from `TextManager` (`data/text/{lang}/...json`), never a literal string in the handler. The **style** (color) is a presentation decision and may live in `keyboards/keyboard_maker.py` as a small config mapping (button-key → style), not scattered as literal `"success"`/`"danger"` strings across every handler:

```python
# app/keyboards/keyboard_maker.py
BUTTON_STYLES = {
    "join_lobby": "success",
    "leave_lobby": "danger",
    "start_new_game": "primary",
    "force_start_confirm": "success",
    "force_start_cancel": "danger",
    # buttons not listed here get no style (default)
}
```
This keeps `keyboard_maker.py` as the single place that knows about styling, consistent with its existing "generic keyboard builder" responsibility.

## Deliverable format when asked to "design the start menu"
1. List every button on the screen.
2. For each, state the assigned style and a one-line reason (tied to the semantic rule above, not "looks nice").
2. Provide the `BUTTON_STYLES` mapping snippet.
3. Note any button using `icon_custom_emoji_id` and flag that it's conditional on bot Premium/extra-username status, so it degrades gracefully (button still works, just without the icon) if unavailable.
