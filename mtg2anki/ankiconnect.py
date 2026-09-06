"""Adding notes to a running desktop Anki via the AnkiConnect add-on."""

import requests

from mtg2anki.config import ANKICONNECT_URL


def invoke(action, **params):
    """Call AnkiConnect API"""
    response = requests.post(ANKICONNECT_URL, json={
        "action": action,
        "version": 6,
        "params": params,
    })
    result = response.json()
    if result.get("error"):
        raise Exception(f"AnkiConnect error: {result['error']}")
    return result["result"]


def find_note_by_front(card_name):
    """Find a note by its Front field value"""
    try:
        note_ids = invoke("findNotes", query=f'"Front:{card_name}"')
        if note_ids:
            return note_ids[0]  # Return the first matching note
        return None
    except Exception:
        return None


def update_note(note_id, card_id, deck_name, log):
    """Update an existing note's UUID and deck"""
    try:
        invoke("updateNoteFields", note={
            "id": note_id,
            "fields": {
                "UUID": card_id,
            },
        })
        # Move to the correct deck
        invoke("changeDeck", cards=[note_id], deck=deck_name)
        log(f"  Updated note ID {note_id} with UUID and moved to deck")
        return True
    except Exception as e:
        log(f"  Error updating note {note_id}: {e}")
        return False


def add_note(card, note, log):
    """Create a note in Anki via AnkiConnect, or update if it exists"""
    card_name = card["name"]

    # Check if note already exists
    existing_note_id = find_note_by_front(card_name)
    if existing_note_id:
        log(f"  Note '{card_name}' already exists, updating...")
        update_note(existing_note_id, card["id"], note.deck, log)
        return existing_note_id

    payload = {
        "deckName": note.deck,
        "modelName": note.note_type,
        "fields": note.fields,
        "options": {
            "allowDuplicate": False,
        },
    }

    try:
        layout = card.get("layout", "normal")
        card_type = layout if layout in ["saga", "adventure"] else "card"
        log(f"  Creating new {card_type}: {card_name} in deck {note.deck}")
        note_id = invoke("addNote", note=payload)
        log(f"  Successfully created note ID: {note_id}")
        return note_id
    except Exception as e:
        log(f"  Error adding note '{card_name}': {e}")
        raise
