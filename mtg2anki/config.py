"""Project configuration, read from config.toml at the repo root."""

import tomllib
from pathlib import Path

# Repo root: this file lives at <root>/mtg2anki/config.py
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.toml"
LOG_FILE = ROOT_DIR / "card-monitor.log"

ANKICONNECT_URL = "http://localhost:8765"

# Scryfall requires a User-Agent and Accept header; requests without them get a
# 400. Reused for 17lands too, since it's just a generic User-Agent/Accept pair.
API_HEADERS = {
    "User-Agent": "mtg2anki/1.0",
    "Accept": "application/json",
}


class ConfigError(Exception):
    """Raised when the set code can't be determined"""


def load_config(path=None):
    """Parse config.toml, raising ConfigError if it's missing or unreadable"""
    path = Path(path) if path is not None else CONFIG_FILE
    if not path.exists():
        raise ConfigError(f'{path} not found. Create it with:\n\n    set = "xyz"\n')
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError) as e:
        raise ConfigError(f"Could not read {path}: {e}")


def resolve_set_code(path=None):
    """Read the set code from config.toml, raising ConfigError if unusable"""
    config = load_config(path)
    set_code = config.get("set")
    if not isinstance(set_code, str) or not set_code.strip():
        raise ConfigError(
            f'{path or CONFIG_FILE} must define a non-empty `set`, e.g. set = "xyz"'
        )
    return set_code.strip().lower()


def state_file(set_code):
    """Path to the state file tracking imported cards for this set"""
    return ROOT_DIR / f"{set_code}_state.json"
