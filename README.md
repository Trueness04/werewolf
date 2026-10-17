# Onyx

Telegram Werewolf (Mafia) game bot — a Python rewrite of a legacy PHP codebase.
Onyx runs the full werewolf gameplay loop inside Telegram groups (lobby → night →
day → vote/lynch → win resolution), backed by PostgreSQL and Redis, with an AI
lobby agent and a React Telegram Mini App for social/economy features.

## Project Layout

The repository root contains a single project folder, `onyx/`:

```
onyx/
├── app/            # Bot core code
│   ├── main.py             # Bot entrypoint / run()
│   ├── handlers/           # Telegram command & callback handlers
│   ├── managers/           # Game logic (phases, roles, votes, wins, economy…)
│   ├── class/              # Domain models: Game, Player, GameMode, Roles
│   ├── database/           # SQLAlchemy async models + schema bootstrap
│   ├── cache/              # Redis client & key registry
│   ├── config/             # Settings & paths
│   ├── filters/            # Custom PTB message filters
│   └── keyboards/          # Inline / reply keyboard builders
├── AI/             # AI lobby agent (personas, brain, LLM client, runner)
├── webapp/         # FastAPI backend + React Telegram Mini App
│   ├── main.py             # FastAPI app (serves API + built UI)
│   ├── api/                # Routes: auth, meta, social, admin
│   ├── ui/                 # React + Vite + TypeScript source
│   └── dist/               # Built frontend assets
├── data/
│   ├── config/     # Game rules as JSON (roles, modes, phases, weights…)
│   ├── text/       # i18n strings (fa / en)
│   ├── env/        # example.env + requirements.txt
│   ├── docs/       # Sprint specs and decision documents (source of truth)
│   ├── tests/      # pytest suite
│   ├── gatekeeper/ # Gatekeeper constraints
│   ├── archive/    # Raw legacy PHP archive (not executable)
│   └── AGENTS.md   # Mandatory project rules (Persian)
└── launcher.py     # Single unified entrypoint: bot + webapp + DB schema
```

## Architecture

- **launcher.py** is the only entrypoint. Startup order:
  1. `Gatekeeper` enforces project structure/style constraints.
  2. DB schema is created/migrated (`app.database.bootstrap.ensure_schema`).
  3. The FastAPI webapp starts in a daemon thread (uvicorn).
  4. The Telegram bot runs in the main thread (`app.main.run`).
- **Game logic** lives in `app/managers/` and is driven by declarative JSON
  ordering files in `data/config/` (e.g. `night_resolution_order.json`,
  `day_resolution_order.json`, `roles.json`, `game_modes.json`).
- **Text/messages** are loaded through TextManager from `data/text/` (i18n,
  default language `fa`).
- **Webapp** handles out-of-bot features: shop, charging, magic store, hero,
  achievements, ranks, profile. The wallet stays in the bot (`/mycoin`,
  `/sendcoin`); the shop links out to the Mini App.
- **AI module** provides bot-to-bot lobby agents (configurable via
  `AI_BOT_TOKEN` / `AI_BOT_USERNAME` and `data/config/ai_agents.json`).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Bot framework | python-telegram-bot (async) ≥20, <22 |
| Web framework | FastAPI + uvicorn |
| Database | PostgreSQL via SQLAlchemy 2.x (async) + asyncpg |
| Cache / state | Redis ≥5 |
| Logging | loguru |
| Frontend | React 19, Vite, TypeScript, telegram-web-app types |
| Tests | pytest + pytest-asyncio |

No MongoDB.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+ (only for building the Mini App UI)
- PostgreSQL and Redis instances

### Setup

```bash
cd onyx

# 1. Install Python dependencies
pip install -r data/env/requirements.txt

# 2. Configure environment
cp data/env/example.env data/env/.env
# edit .env: BOT_TOKEN, DB_*, REDIS_*, WEBAPP_URL, SUDO_IDS …

# 3. Build the webapp frontend (optional — needed for the Mini App)
cd webapp/ui
npm install
npm run build      # output goes to webapp/dist
cd ../..

# 4. Run everything
python -u launcher.py
```

### Development

Run the UI dev server with API proxying to port 8080:

```bash
cd webapp/ui
npm run dev
```

Run tests:

```bash
pytest data/tests
```

## Key Environment Variables

| Variable | Meaning | Default |
|----------|---------|---------|
| `BOT_TOKEN` | Telegram bot token | — |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL connection | localhost / 5432 / onyx_db |
| `REDIS_HOST` / `REDIS_PORT` | Redis connection | localhost / 6379 |
| `WEBAPP_HOST` | Webapp bind host | `0.0.0.0` |
| `WEBAPP_PORT` | Webapp bind port | `8080` |
| `WEBAPP_URL` | Public Mini App URL (required for Telegram Mini App) | empty |
| `SUDO_IDS` | Sudo administrator user IDs | — |
| `DEFAULT_LANG` / `FALLBACK_LANG` | i18n languages | `fa` / `en` |
| `DEBUG_MODE` | Verbose logging | `false` |
| `ENABLE_BOT_TO_BOT` / `AI_BOT_TOKEN` / `AI_BOT_USERNAME` | AI lobby agent | — |

Phase timing (`NIGHT_DURATION_SECONDS`, `DAY_DURATION_SECONDS`,
`VOTE_DURATION_SECONDS`), lobby limits (`JOIN_DURATION_SECONDS`, `MAX_PLAYERS`,
`EXTEND_DEFAULT_SECONDS`) and economy values (`JOIN_COST_COINS`) are also set
in `.env` — see `data/env/example.env` for the full list.

## Project Rules (Gatekeeper)

This project enforces strict structural and style rules, documented in
[`onyx/data/AGENTS.md`](onyx/data/AGENTS.md):

- Root `onyx/` may contain **only** `app/`, `data/`, `AI/`, `webapp/` and
  `launcher.py`.
- ≤ 350 lines per file, ≤ 78 characters per line.
- Long string literals only inside `data/`.
- Secrets only in `data/env/.env`.
- Game rules live in `data/config/*.json`; role definitions in
  `data/config/roles.json`.
- Source of truth for product decisions: `data/docs/sprint-index-fa.md` and
  related sprint documents.

Additional docs: [`onyx/webapp/README.md`](onyx/webapp/README.md) (Mini App)
and [`onyx/webapp/ADMIN.md`](onyx/webapp/ADMIN.md) (admin panel).

## License

Private / internal project. All rights reserved.
