#!/usr/bin/env python3
"""
Scryfall to Anki Importer
Monitors Scryfall for new cards and imports them directly to Anki via AnkiConnect
"""

import json
from datetime import datetime

from mtg2anki.anki import ankiconnect_available, invoke_ankiconnect
from mtg2anki.cards import CLOZE_LAYOUTS, note_for_layout
from mtg2anki.config import (
    ConfigError,
    LOG_FILE,
    ROOT_DIR,
    resolve_set_code,
    state_file,
)
from mtg2anki.scryfall import fetch_set_info, scryfall_get

# ===== HELPER FUNCTIONS =====

def log_message(message):
    """Log message to file and print to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - {message}"
    print(log_entry)
    with open(LOG_FILE, "a") as f:
        f.write(log_entry + "\n")

def fetch_scryfall_cards(set_code):
    """Fetch cards from Scryfall API"""
    query = f"set:{set_code} r<r -type:basic"
    url = f"https://api.scryfall.com/cards/search?q={query}&order=spoiled"

    all_cards = []
    while url:
        response = scryfall_get(url, log=log_message)
        data = response.json()

        for card in data.get("data", []):
            if '"' not in card["name"]:
                all_cards.append({
                    "name": card["name"],
                    "id": card["id"],
                    "layout": card.get("layout", "normal"),
                    "card_faces": card.get("card_faces", [])
                })

        url = data.get("next_page")

    log_message(f"Found {len(all_cards)} cards")
    return all_cards

def load_state(set_code):
    """Load previously seen card IDs for this set"""
    path = state_file(set_code)
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {"card_ids": []}

def save_state(set_code, card_ids):
    """Save current card IDs to this set's state file"""
    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    with open(state_file(set_code), "w") as f:
        json.dump({"card_ids": card_ids}, f, indent=2)

def find_existing_note(card_name, card_id):
    """Find a note matching this card by UUID (any layout) or Front (regular cards)"""
    try:
        note_ids = invoke_ankiconnect("findNotes", query=f'"UUID:{card_id}"')
        if note_ids:
            return note_ids[0]
        note_ids = invoke_ankiconnect("findNotes", query=f'"Front:{card_name}"')
        if note_ids:
            return note_ids[0]
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

def create_anki_note(card_name, card_id, layout, deck_name, card_faces=None):
    """Create a note in Anki via AnkiConnect, or update if it exists"""
    note_type, fields = note_for_layout(card_name, card_id, layout, card_faces)

    # Check if note already exists
    existing_note_id = find_existing_note(card_name, card_id)
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
        card_type = layout if layout in CLOZE_LAYOUTS else "card"
        log_message(f"  Creating new {card_type}: {card_name} in deck {deck_name}")
        note_id = invoke_ankiconnect("addNote", note=note)
        log_message(f"  Successfully created note ID: {note_id}")
        return note_id
    except Exception as e:
        log_message(f"  Error adding note '{card_name}': {e}")
        raise

def import_new_cards(new_cards, deck_name):
    """Import new cards to Anki, returning the set of card IDs that succeeded"""
    if not new_cards:
        log_message("No new cards to import")
        return set()

    log_message(f"Importing {len(new_cards)} new cards to Anki...")

    imported_ids = set()
    for card in new_cards:
        try:
            note_id = create_anki_note(
                card["name"],
                card["id"],
                card["layout"],
                deck_name,
                card.get("card_faces")
            )
            if note_id:
                imported_ids.add(card["id"])
        except Exception as e:
            log_message(f"  Error importing '{card['name']}': {e}")

    log_message(f"Successfully imported {len(imported_ids)} of {len(new_cards)} cards")
    return imported_ids

def main():
    """Main execution"""
    try:
        set_code = resolve_set_code()
    except ConfigError as e:
        log_message(f"Configuration error: {e}")
        raise SystemExit(1)

    log_message("=" * 60)
    log_message("Starting Scryfall to Anki import check")

    try:
        if not ankiconnect_available(log=log_message):
            log_message("Aborting: Anki/AnkiConnect is not running. Will retry on next run.")
            return

        # Fetch set info
        set_info = fetch_set_info(set_code, log=log_message)
        deck_name = f"Main::MTG::{set_info['name']}"
        log_message(f"Set: '{set_info['name']}' ({set_code})")
        log_message(f"Target deck: {deck_name}")

        # Fetch current cards from Scryfall
        current_cards = fetch_scryfall_cards(set_code)
        current_card_ids = set(card["id"] for card in current_cards)

        # Load previous state
        state = load_state(set_code)
        previous_card_ids = set(state.get("card_ids", []))

        log_message(f"Current cards: {len(current_card_ids)}, Previously imported: {len(previous_card_ids)}")

        # Cards we haven't successfully imported yet (includes prior failures)
        pending_ids = current_card_ids - previous_card_ids

        if not pending_ids:
            log_message("No new cards detected")
            return

        pending_cards = [card for card in current_cards if card["id"] in pending_ids]
        log_message(f"Detected {len(pending_cards)} cards to import (new or previously failed)")

        imported_ids = import_new_cards(pending_cards, deck_name)

        # Persist only successes, scoped to cards still present on Scryfall
        new_state_ids = (previous_card_ids | imported_ids) & current_card_ids
        save_state(set_code, sorted(new_state_ids))

        failed = len(pending_cards) - len(imported_ids)
        if failed:
            log_message(f"{failed} cards failed; will retry on next run")

    except Exception as e:
        log_message(f"Error: {e}")
        import traceback
        log_message(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
