"""Project path constants (relative roots only)."""

from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]

APP_DIR: Path = ROOT / "app"
DATA_DIR: Path = ROOT / "data"
TEXT_DIR: Path = DATA_DIR / "text"
LOGS_DIR: Path = DATA_DIR / "logs"
CONSOLE_DIR: Path = DATA_DIR / "console"
ENV_DIR: Path = DATA_DIR / "env"
GK_DIR: Path = DATA_DIR / "gatekeeper"
CONFIG_DATA: Path = DATA_DIR / "config"

ERRORS_JSON: Path = TEXT_DIR / "errors.json"
URL_TEMPLATES: Path = CONFIG_DATA / "url_templates.json"
GAME_MODES: Path = CONFIG_DATA / "game_modes.json"
COMMANDS_JSON: Path = CONFIG_DATA / "commands.json"
WARNING_SECONDS: Path = (
    CONFIG_DATA / "warning_seconds.json"
)
GAME_PHASES: Path = CONFIG_DATA / "game_phases.json"
REDIS_KEYS: Path = CONFIG_DATA / "redis_keys.json"
LOGGING_SETTINGS: Path = (
    CONFIG_DATA / "logging_settings.json"
)
LOG_MESSAGES: Path = CONFIG_DATA / "log_messages.json"
ROLES_JSON: Path = CONFIG_DATA / "roles.json"
ROLE_WEIGHTS: Path = CONFIG_DATA / "role_weights.json"
WOLF_COUNT_TABLE: Path = (
    CONFIG_DATA / "wolf_count_table.json"
)
ROLE_FILL: Path = CONFIG_DATA / "role_fill.json"
NIGHT_ORDER: Path = (
    CONFIG_DATA / "night_resolution_order.json"
)
GAME_MODE_ROLES: Path = (
    CONFIG_DATA / "game_mode_roles.json"
)
ROLE_CLASS_MAP: Path = (
    CONFIG_DATA / "role_class_map.json"
)
CALLBACK_TEMPLATES: Path = (
    CONFIG_DATA / "callback_templates.json"
)
DAY_ORDER: Path = (
    CONFIG_DATA / "day_resolution_order.json"
)
LYNCH_ORDER: Path = (
    CONFIG_DATA / "lynch_post_order.json"
)
DAY_ROLES: Path = CONFIG_DATA / "day_roles.json"
WIN_CODES: Path = CONFIG_DATA / "win_codes.json"
WIN_TEAM_MAP: Path = CONFIG_DATA / "win_team_map.json"
AI_AGENTS: Path = CONFIG_DATA / "ai_agents.json"
AI_PERSONAS: Path = CONFIG_DATA / "ai_personas.json"
GK_STRUCTURE: Path = GK_DIR / "structure.json"
GK_PATTERNS: Path = GK_DIR / "patterns.json"
GK_LIMITS: Path = GK_DIR / "limits.json"
GK_CONSOLE: Path = CONSOLE_DIR / "gatekeeper.json"
LOG_CONSOLE: Path = CONSOLE_DIR / "logging.json"
APP_CONSOLE: Path = CONSOLE_DIR / "app.json"
EXAMPLE_ENV: Path = ENV_DIR / "example.env"
DOTENV_FILE: Path = ENV_DIR / ".env"
REQUIREMENTS: Path = ENV_DIR / "requirements.txt"

LAUNCHER: Path = ROOT / "launcher.py"

SUPPORTED_LANGS: tuple[str, ...] = (
    "fa",
    "en",
    "ar",
    "zh",
    "id",
    "es",
)
