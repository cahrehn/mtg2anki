#!/usr/bin/env python3
"""
Scryfall to Anki Importer
Monitors Scryfall for new cards and imports them directly to Anki via AnkiConnect
"""

import requests
import json
import os
import time
from datetime import datetime
from pathlib import Path

# ===== CONFIGURATION =====
SET_CODE = "tla"  # MTG set code to monitor
MTG_NOTE_TYPE = "MTG Text Box"  # Anki note type for regular cards
SAGA_NOTE_TYPE = "MTG Saga"  # Anki note type for saga cards
ADVENTURE_NOTE_TYPE = "MTG Adventure"  # Anki note type for adventure cards
ANKICONNECT_URL = "http://localhost:8765"

# Scryfall requires a User-Agent and Accept header; requests without them get a 400
SCRYFALL_HEADERS = {
    "User-Agent": "mtg2anki/1.0",
    "Accept": "application/json",
}

# File paths
SCRIPT_DIR = Path.home() / "dev" / "mtg2anki"
STATE_FILE = SCRIPT_DIR / f"{SET_CODE}_state.json"
LOG_FILE = SCRIPT_DIR / "card-monitor.log"

# ===== HELPER FUNCTIONS =====

def log_message(message):
    """Log message to file and print to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - {message}"
    print(log_entry)
    with open(LOG_FILE, "a") as f:
        f.write(log_entry + "\n")

def invoke_ankiconnect(action, **params):
    """Call AnkiConnect API"""
    response = requests.post(ANKICONNECT_URL, json={
        "action": action,
        "version": 6,
        "params": params
    })
    result = response.json()
    if result.get("error"):
        raise Exception(f"AnkiConnect error: {result['error']}")
    return result["result"]

def ankiconnect_available():
    """Return True if AnkiConnect responds on localhost"""
    try:
        invoke_ankiconnect("version")
        return True
    except Exception as e:
        log_message(f"AnkiConnect not reachable: {e}")
        return False

def scryfall_get(url, attempts=4):
    """GET a Scryfall URL with retries on transient failures"""
    delay = 2
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, headers=SCRYFALL_HEADERS, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == attempts:
                raise
            log_message(f"  Scryfall request failed ({e}); retry {attempt}/{attempts - 1} in {delay}s")
            time.sleep(delay)
            delay *= 2

def fetch_set_info(set_code):
    """Fetch set information from Scryfall API"""
    url = f"https://api.scryfall.com/sets/{set_code}"
    response = scryfall_get(url)
    data = response.json()
    return {
        "code": data["code"],
        "name": data["name"],
        "released_at": data.get("released_at", "Unknown")
    }

def fetch_scryfall_cards(set_code):
    """Fetch cards from Scryfall API"""
    query = f"set:{set_code} r<r -type:basic -is:dfc"
    url = f"https://api.scryfall.com/cards/search?q={query}&order=spoiled"

    all_cards = []
    while url:
        response = scryfall_get(url)
        data = response.json()

        for card in data.get("data", []):
            if '"' not in card["name"]:
                all_cards.append({
                    "name": card["name"],
                    "id": card["id"],
                    "layout": card.get("layout", "normal")
                })

        url = data.get("next_page")

    log_message(f"Found {len(all_cards)} cards")
    return all_cards

def load_state():
    """Load previously seen card IDs"""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"card_ids": []}

def save_state(card_ids):
    """Save current card IDs to state file"""
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump({"card_ids": card_ids}, f, indent=2)

def find_note_by_front(card_name):
    """Find a note by its Front field value"""
    try:
        note_ids = invoke_ankiconnect("findNotes", query=f'"Front:{card_name}"')
        if note_ids:
            return note_ids[0]  # Return the first matching note
        return None
    except Exception:
        return None

def update_note(note_id, card_id, deck_name):
    """Update an existing note's UUID and deck"""
    try:
        invoke_ankiconnect("updateNoteFields", note={
            "id": note_id,
            "fields": {
                "UUID": card_id
            }
        })
        # Move to the correct deck
        invoke_ankiconnect("changeDeck", cards=[note_id], deck=deck_name)
        log_message(f"  Updated note ID {note_id} with UUID and moved to deck")
        return True
    except Exception as e:
        log_message(f"  Error updating note {note_id}: {e}")
        return False

def create_anki_note(card_name, card_id, layout, deck_name):
    """Create a note in Anki via AnkiConnect, or update if it exists"""
    if layout == "saga":
        note_type = SAGA_NOTE_TYPE
        fields = {
            "Front": card_name,
            "UUID": card_id
        }
    elif layout == "adventure":
        note_type = ADVENTURE_NOTE_TYPE
        fields = {
            "Text": f"{{{{c1::adventure}}}} {{{{c2::permanent}}}} {card_name}",
            "UUID": card_id
        }
    else:
        note_type = MTG_NOTE_TYPE
        fields = {
            "Front": card_name,
            "UUID": card_id
        }

    # Check if note already exists
    existing_note_id = find_note_by_front(card_name)
    if existing_note_id:
        log_message(f"  Note '{card_name}' already exists, updating...")
        update_note(existing_note_id, card_id, deck_name)
        return existing_note_id

    # Create new note
    note = {
        "deckName": deck_name,
        "modelName": note_type,
        "fields": fields,
        "options": {
            "allowDuplicate": False
        }
    }

    try:
        card_type = layout if layout in ["saga", "adventure"] else "card"
        log_message(f"  Creating new {card_type}: {card_name} in deck {deck_name}")
        note_id = invoke_ankiconnect("addNote", note=note)
        log_message(f"  Successfully created note ID: {note_id}")
        return note_id
    except Exception as e:
        log_message(f"  Error adding note '{card_name}': {e}")
        raise

def import_new_cards(new_cards, deck_name):
    """Import new cards to Anki"""
    if not new_cards:
        log_message("No new cards to import")
        return

    log_message(f"Importing {len(new_cards)} new cards to Anki...")

    imported_count = 0
    for card in new_cards:
        try:
            note_id = create_anki_note(card["name"], card["id"], card["layout"], deck_name)
            if note_id:
                imported_count += 1
        except Exception as e:
            log_message(f"  Error importing '{card['name']}': {e}")

    log_message(f"Successfully imported {imported_count} cards")

def main():
    """Main execution"""
    log_message("=" * 60)
    log_message("Starting Scryfall to Anki import check")

    try:
        if not ankiconnect_available():
            log_message("Aborting: Anki/AnkiConnect is not running. Will retry on next run.")
            return

        # Fetch set info
        set_info = fetch_set_info(SET_CODE)
        deck_name = f"Main::MTG::{set_info['name']}"
        log_message(f"Set: '{set_info['name']}' ({SET_CODE})")
        log_message(f"Target deck: {deck_name}")

        # Fetch current cards from Scryfall
        current_cards = fetch_scryfall_cards(SET_CODE)
        current_card_ids = [card["id"] for card in current_cards]

        # Load previous state
        state = load_state()
        previous_card_ids = state.get("card_ids", [])

        log_message(f"Current cards: {len(current_card_ids)}, Previous cards: {len(previous_card_ids)}")

        # Check if this is the first run
        if not previous_card_ids:
            log_message("Initial run - importing all cards")
            # Treat all cards as new on first run
            new_cards = current_cards
            import_new_cards(new_cards, deck_name)
            save_state(current_card_ids)
            return

        # Find new cards
        new_card_ids = set(current_card_ids) - set(previous_card_ids)

        if new_card_ids:
            new_cards = [card for card in current_cards if card["id"] in new_card_ids]
            log_message(f"Detected {len(new_cards)} new cards!")

            # Import to Anki
            import_new_cards(new_cards, deck_name)

            # Update state file
            save_state(current_card_ids)
        else:
            log_message("No new cards detected")

    except Exception as e:
        log_message(f"Error: {e}")
        import traceback
        log_message(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
