"""Configuration shared by the desktop and feed entry points."""

import json
import os
from pathlib import Path

# ===== CONFIGURATION =====
SET_CODE = os.environ.get("MTG2ANKI_SET", "tla")  # set the desktop run imports
MTG_NOTE_TYPE = "MTG Text Box"  # Anki note type for regular cards and sagas
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
FEEDS_FILE = REPO_DIR / "feeds.json"  # feed name -> set code

# Handed to AnkiMobile as x-success so a running Shortcut resumes after each add
X_SUCCESS_URL = os.environ.get("MTG2ANKI_X_SUCCESS", "shortcuts://")


def state_file(set_code):
    """Desktop state file (list of card IDs already imported via AnkiConnect)."""
    return SCRIPT_DIR / f"{set_code}_state.json"


def feeds():
    """Feed name -> {"set": code, "cards": path or None}, from feeds.json.

    An entry is either a bare set code, or an object naming a card list to
    limit the feed to: {"set": "dmu", "cards": "cards/dmu.txt"}.

    Each named feed gets its own feed/<name>.json and its own sequence
    numbering, so a second set can be published alongside the main one without
    disturbing it. MTG2ANKI_SET overrides the set code of the "current" feed.
    """
    with open(FEEDS_FILE) as f:
        configured = json.load(f)
    override = os.environ.get("MTG2ANKI_SET")
    if override:
        configured["current"] = override

    specs = {}
    for name, spec in configured.items():
        if isinstance(spec, str):
            spec = {"set": spec}
        cards = spec.get("cards")
        specs[name] = {
            "set": spec["set"],
            "cards": REPO_DIR / cards if cards else None,
        }
    return specs


def feed_file(name):
    return FEED_DIR / f"{name}.json"


def feed_state_file(name):
    """Feed state file (card ID -> sequence number), committed to the repo.

    Sequence numbers only ever climb within a feed, so the phone's saved
    cursor keeps working when the feed switches to a new set.
    """
    return FEED_STATE_DIR / f"{name}.json"


def deck_name(set_name):
    return f"{DECK_PREFIX}::{set_name}"
