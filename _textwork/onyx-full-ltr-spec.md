## Workflow Rules — Amin 0905 (Plan B live)
1. NEVER ask 'شروع کنم؟' — act immediately once task is defined
2. Auto-orchestrate by default: multi-agent (delegate_task) is the default execution path
3. Fresh pattern per task — invent on the spot
4. Report = short Persian bullets, real verified output only
5. After every chat, persist lasting facts to mem0/skill
6. Boot = read ~/.hermes/harness/task-queue.md + execute oldest ready task

## Escalation (Plan A fallback)
If a real auto-fire failure happens (clear evidence: harness didn't run, queue missed, etc.):
→ Wire pre_llm_call shell-hook enforcing the orchestrator, via hermes hooks.
Trigger condition: documented failure + Amin approval for the exact hook command.

---


## Code location
Edit: `~/Project/onyx` (WSL). Runtime: Railway (guest identical).

## Roster tables (both lists)
- Header row = `Players`, `Status`, `Role` (content-carrying)
- Body: `#Players (N/N)` where N/N = alive/total
- FULL LTR (`\u2066…\u2069`) everywhere — FA + Latin names/groups alike
- Empty custom-emoji column: player CHOOSES their custom emoji ingame; if none yet, blank

## Phase list (between phases)
`custom | Name [medal] | 🙂/☠️ | Role (if dead)`

## End-game win list
`custom | Name [medal] | 🥇/⚫️ | 🙂/☠️ | Role` — roles revealed for EVERYONE incl. alive winners. Win list ALWAYS follows the win announcement.

## Medals (Nix algorithm)
Tiers in `app/managers/nix_medals.py`: · 0 → 🗡 10g → 🪦 30g → 📜 60g+5w → 🏛 100g+10w → 👑 150g+25w → 🏆 250g+50w
Role emojis + medal emojis + 🥇⚫️🙂☠️ = RESERVED; picker must refuse them as custom emojis.

## Lobby
Old 3-cell numbered seat = useless → remove. Custom-emoji column must fit. Verify join-lobby message pinning (start_game.py:313 → bridge.pin).

## Working mode (0905, supersedes)
Begin execution immediately when task defined — no "شروع کنم؟". Full autonomy: remove approval gates, Nix decides. Every task: fresh pattern invented on the spot. Default = orchestrated multi-agent workflow. Always update memory/skill after user chat, safely.
