---
name: onyx-language-pack-authoring
description: >-
  Author, complete, and expand Onyx werewolf-bot "flavor pack" translation/text
  files — alternate dialogue and story tone variants (e.g. NSFW, rude/impolite,
  "forgetful", nightclub, mafia-NSFW) that reuse the exact same game mechanics
  but swap the narrative voice. Use this skill whenever working with Onyx's
  data/text/{lang} JSON files, adding a new game-mode text variant, moving mode
  selection into the group settings panel, or translating an existing pack into
  another language while preserving its tone. Also use whenever the user
  mentions "flavor pack", "زبان بی‌ادبی", "زبان فراموشی", "NightClub mode",
  "NSFW mode", or reference folder E:\html\Languages.
---

# Onyx Language Pack Authoring

## Core concept — packs are tone, not mechanics

A "mode" in this project is **not** a gameplay variant. The state machine,
roles, timers, and win conditions are identical across every mode. The only
thing that changes between modes is the **narrative voice** of the exact same
message keys: who's talking, how polite/rude/horny/forgetful they sound, and
the flavor text wrapped around identical placeholders (`{0}`, `{1}`, ...).

Treat every pack as a **translation of tone**, the same way `fa` vs `en` is a
translation of language. A pack is valid only if it has 1:1 key parity with
the canonical base pack — never more keys, never fewer.

## Known packs (reference only — source lives at `E:\html\Languages`, not in the repo)

- `Persian` — base/neutral tone, fa (completed)
- `English` — base/neutral tone, en (completed)
- `PersianNSFW` / `EnglishNSFW` — adult/suggestive tone
- `SpanishNSFWYMCA` — adult/suggestive tone, es
- `NightClub Mode` (Persian) — flirtatious/party tone
- `Persian mafia NSFW` — gritty crime-family tone, adult
- Rude/"forgetful" tone packs mentioned by the user are new additions, not yet
  in the reference folder — treat them as packs to be authored from scratch
  against the canonical key list, not translated from an existing file.

`E:\html\Languages` is the user's local Windows path for the legacy PHP source
material — it will never be reachable from this environment. When the user
references it, ask them to paste the relevant `.ini`/text content rather than
trying to read the path directly.

## Target languages (per Onyx's established stack)

`fa, en, ar, zh, id, es` — every pack must eventually exist in all six. `fa`
and `en` are usually the first complete pack per mode; `ar, zh, id, es` are
filled in afterward.

## Workflow

### 1. Establish the canonical key list

Before touching any new pack, get (or build) the full list of message keys
from the most complete base pack (Persian or English, non-NSFW). This key
list is the contract every other pack must match exactly — same keys, same
`{n}` placeholder positions, same count.

### 2. Author or translate a pack

For a **new tone variant** (e.g. "rude", "forgetful"):

- Go key by key through the canonical list.
- Rewrite each message in the new voice while preserving:
  - all `{0}`, `{1}`, ... placeholders in the same order
  - the same semantic meaning (a kill message must still communicate a kill)
  - any embedded game-logic tokens (role names, button callback keys)
- Do not invent new keys and do not drop keys that seem to not fit the tone —
  find a tone-consistent way to express every key instead.

For a **translation of an existing pack into a new language**:

- Preserve the *tone* of the source pack. An NSFW pack translated into
  Spanish must stay adult/suggestive in Spanish — do not sanitize it in
  translation, and do not add explicit content beyond what the source pack
  already contains.
- Preserve placeholders and formatting exactly.

### 3. Verify key parity (do this every time, no exceptions)

Diff the new pack's key set against the canonical list:

- Missing keys → the pack is incomplete; do not ship it silently. Report the
  gap to the user rather than inventing filler placeholder text.
- Extra keys → likely a typo or a leftover from a different pack; flag it.
- Placeholder count mismatch on any key → flag it explicitly.

This check matters more here than in ordinary i18n work: Onyx's Gatekeeper
(see project rules) treats any string that isn't sourced correctly from
`data/text/{lang}/` as a hardcoding violation, and a missing key at runtime
means `TextManager` has nothing to serve for that mode.

### 4. Wire mode selection into config, not slash commands

The user wants mode selection moved from separate `/startX` slash commands
into the **group settings panel**. This is a data change, not a code change
per mode:

- Each mode becomes an entry in a config file (e.g.
  `data/config/game_modes.json`) with: mode id, display name key, and which
  language-pack folder set (`data/text/{lang}/<mode>/`) it maps to.
- The settings panel handler reads this config to build the menu — it never
  hardcodes a mode name, folder path, or list of available modes in `.py`.
- Adding a new mode later = adding a JSON entry + six pack files, not writing
  new handler code. This is the entire point of moving modes into config.

## Content boundaries

"NSFW" here means adult/suggestive humor and crude language appropriate to a
party game for adults — not literal explicit sexual content. Keep authored
text at the level of innuendo, crude jokes, and horror-flavored gore
(consistent with the existing werewolf kill/death messages), and stop short
of generating graphic sexual descriptions. If a request pushes past that
line, say so plainly and offer the closest in-bounds version rather than
producing the explicit version.

## Output format

Always output a single JSON file per pack per language (matching Onyx's
existing `data/text/{lang}/*.json` convention), with a short summary listing:
canonical key count, keys covered, and any keys still marked
`TODO_FROM_SOURCE` because the source material didn't specify exact wording.
Never fabricate wording for a key you don't have real source content for —
mark it as a placeholder explicitly, the same way prior Onyx text files did.

## Constraints

- Workspace: E:\Project\onyx
- Do NOT commit unless asked
- Communicate final result in Persian, short
- Follow Onyx root rules: docs live under data/, etc. — skill goes in
  `.cursor/skills` only
