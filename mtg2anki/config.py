"""Configuration shared by the desktop and feed entry points."""

import os
from pathlib import Path

# ===== CONFIGURATION =====
SET_CODE = os.environ.get("MTG2ANKI_SET", "tla")  # MTG set code to monitor
MTG_NOTE_TYPE = "MTG Text Box"  # Anki note type for regular cards
SAGA_NOTE_TYPE = "MTG Saga"  # Anki note type for saga cards
ADVENTURE_NOTE_TYPE = "MTG Adventure"  # Anki note type for adventure cards
DECK_PREFIX = "Main::MTG"  # New cards land in "<prefix>::<set name>"
ANKICONNECT_URL = os.environ.get("ANKICONNECT_URL", "http://localhost:8765")

# Where the desktop (AnkiConnect) run keeps its state and log
SCRIPT_DIR = Path(os.environ.get("MTG2ANKI_DIR", Path.home() / "dev" / "mtg2anki"))
LOG_FILE = SCRIPT_DIR / "card-monitor.log"

# Where the published feed and its state live (inside the repo, committed by CI)
REPO_DIR = Path(__file__).resolve().parent.parent
FEED_DIR = REPO_DIR / "feed"
FEED_STATE_DIR = REPO_DIR / "state"

# Handed to AnkiMobile as x-success so a running Shortcut resumes after each add
X_SUCCESS_URL = os.environ.get("MTG2ANKI_X_SUCCESS", "shortcuts://")


def state_file(set_code):
    """Desktop state file (list of card IDs already imported via AnkiConnect)."""
    return SCRIPT_DIR / f"{set_code}_state.json"


def feed_state_file():
    """Feed state file (card ID -> sequence number), committed to the repo.

    One file across all sets, so sequence numbers keep climbing when the
    monitored set changes and the phone's saved cursor stays meaningful.
    """
    return FEED_STATE_DIR / "feed.json"


def deck_name(set_name):
    return f"{DECK_PREFIX}::{set_name}"
