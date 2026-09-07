---
name: onyx-gatekeeper-compliance
description: Use when editing Onyx app/ files — gatekeeper rules.
---

# Onyx Gatekeeper — THE LAW (Amin's verbatim rules, 2026-09-08)

## Structure (Amin's verbatim law, 2026-09-08)
- root/app/ → *.py files ONLY
- root/data/ → non-*.py files ONLY
- root/launcher.py → the only root-level py
- Anything besides app/, data/, launcher.py → NOT ALLOWED

## Hardcode ban (all forbidden inside *.py)
console/print statements, literal strings, SQL queries, error handling messages, URLs, paths, keys, secrets, regex, ANY text directly in *.py — NOT ALLOWED. Text/config belongs in data/ (json/env).

## Style & size (Amin's verbatim law)
- All PEP8
- Files over 350 lines: NOT ALLOWED
- Lines over 78 chars: NOT ALLOWED

## Extra enforcement (patterns.json)
- literals ≤ 40 chars, docstrings exempt; skip_files currently [paths.py] but Amin calls skip-lists a hiding shortcut — never rely on exemptions, make code compliant
- rules: raw_sql, inline_url, secret_like, abs_windows_path, inline_regex, hardcoded_numeric_id (8+ digits)
- structure.json layout check

Gatekeeper blocks startup on ANY violation. Never bypass, never call pre-existing issues "not ours".

## Proven fix patterns
1. Long loguru templates: split into implicit-concat chunks ≤ 40 chars, keep each {} placeholder intact inside one chunk.
2. Long Persian literals: split at word boundaries into adjacent quoted parts.
3. Long lines: wrap, never rename identifiers.
4. After every batch: py_compile each file, then `timeout 60 python3 launcher.py 2>&1 | grep -c gatekeeper:` → target 0.

## Hard lessons (paid for)
- NEVER bulk word-wrap strings containing {} placeholders — broke 5 files (90 fixes → 5 SyntaxErrors); rollback = git checkout -- <files>.
- loguru templates look like "file: func exc={}", exc — chunking must preserve the exc={} tail.
- Implicit concat "a" "b" = separate literals; each chunk must pass ≤ 40 independently.
- Counts: senior_handler 44, session_senior 25, magic_panel_handler 11, magic_panel 8, magic_panel_keyboard 2, smite_handler 1, ai_toggle 1, chat_bridge 2 (hand-fixed).

## Run protocol
- Local run needs valid BOT_TOKEN in data/env/.env (Amin rotates tokens; never echo values).
- Startup success = gatekeeper count 0, then polling init lines in output.
- After pass, verify with `timeout 30 python3 launcher.py`, check Telegram init, kill after verify.

## Subagent inheritance (mandatory for ANY Onyx code task)
Every subagent dispatched for Onyx code MUST receive this rule block verbatim in its context:
"ONYX LAW: app/ = *.py only, data/ = non-py only, launcher.py only root py. NO hardcodes in *.py: no print/console, literal strings, SQL, error messages, URLs, paths, keys, secrets, regex, any text — text goes to data/ (json/env). PEP8, files ≤350 lines, lines ≤78 chars, literals ≤40 chars. Gatekeeper blocks startup on violations — fix code, never bypass. Edit ONLY files Amin approved; nothing else."
A subagent that violates: its changes get reverted, no second chance. Verification duty (commander): re-run gatekeeper count + py_compile on every file the child touched BEFORE reporting to Amin.

## Authority rules (paid for 2026-09-08)
- Nix does NOT hold standing write-access to Onyx. Each edit batch needs Amin's explicit per-task go.
- Amin decides scope; never inflate a granted permission into blanket access (strike #4).
- When a gatekeeper result looks unfair, the code is wrong — the tool is never negotiated with.
- Exemption lists (skip_files) are not cover: make the code compliant instead.
- Command is law: launcher reports user-visible facts; bulk auto-fixes of loguru templates are FORBIDDEN (5 files broke once).