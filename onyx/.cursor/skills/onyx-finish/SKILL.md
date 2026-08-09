---
name: onyx-finish
description: >-
  Finish the Onyx Python Telegram Werewolf rewrite against data/docs.
  Use when the user asks to complete Onyx, continue sprints, apply remediation
  MF fixes, remove Bomber/coin, or ship playable parity from sprint-index.
---

# Onyx finish agent

## Source of truth
1. data/docs/sprint-index-fa.md — entry + order
2. data/docs/remediation-accepted-fixes-fa.md — locked fix/remove
3. data/docs/acceptance-backlog-mirror-fix-fa.md — MF matrix
4. Sprint docs sprint-01 … sprint-11 for behavior

## Hard product locks
- **remove:** Bomber role/mode/BombCount; game mode coin; /bet+dead bet callbacks; empty Achio stubs
- **keep:** dynamite; bot wallet only (/mycoin,/sendcoin); shop on webapp
- **product-new** (change-spec senior/RoleLink/webapp): only if user explicitly asks
- **Foolish MF-15:** mirror = exactly 1 wolf unless user says fix

## Engineering constraints
- Entry: python -u launcher.py
- Gatekeeper always: max 350 lines/file, 78 chars/line
- Split files before hitting limits; no commits unless asked
- Prefer managers + JSON config over fat role classes
- Persian concise status only when user asks; otherwise ship code

## Finish order (core playable)
1. Remediation accepted gaps still open in code
2. Night/day/vote/lynch/win parity per sprints 1–8
3. Lobby/roles per sprint-09 (no Bomber/coin)
4. Commands/callbacks sprint-10 + MF-26 always answer callbacks
5. Tick loop sprint-11
6. Economy bot = wallet-only; full shop deferred to webapp
7. Tests for MF acceptance criteria when touching that path

## Do not
- Reintroduce Bomber or coin mode
- Mirror hardcoded secrets (MF-23)
- Expand scope to webapp change-spec without ask
- Write markdown docs unless asked
