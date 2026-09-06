#!/usr/bin/env python3
"""
Scryfall to Anki Importer
Monitors Scryfall for new cards and imports them directly to Anki via AnkiConnect.

Needs desktop Anki running with AnkiConnect. For a phone-friendly run, use
build_feed.py instead - see docs/iphone.md.
"""

from mtg2anki import ankiconnect, config, scryfall
from mtg2anki.log import make_logger
from mtg2anki.notes import build_note
from mtg2anki.state import load_seen_ids, save_seen_ids

log_message = make_logger(config.LOG_FILE)


def import_new_cards(new_cards, deck_name):
    """Import new cards to Anki"""
    if not new_cards:
        log_message("No new cards to import")
        return

    log_message(f"Importing {len(new_cards)} new cards to Anki...")

    imported_count = 0
    for card in new_cards:
        try:
            note = build_note(card, deck_name)
            if ankiconnect.add_note(card, note, log_message):
                imported_count += 1
        except Exception as e:
            log_message(f"  Error importing '{card['name']}': {e}")

    log_message(f"Successfully imported {imported_count} cards")


def main():
    """Main execution"""
    log_message("=" * 60)
    log_message("Starting Scryfall to Anki import check")

    set_code = config.SET_CODE
    state_file = config.state_file(set_code)

    try:
        # Fetch set info
        set_info = scryfall.fetch_set_info(set_code)
        deck_name = config.deck_name(set_info["name"])
        log_message(f"Set: '{set_info['name']}' ({set_code})")
        log_message(f"Target deck: {deck_name}")

        # Fetch current cards from Scryfall
        current_cards = scryfall.fetch_cards(set_code, log_message)
        current_card_ids = [card["id"] for card in current_cards]

        # Load previous state
        previous_card_ids = load_seen_ids(state_file)

        log_message(f"Current cards: {len(current_card_ids)}, Previous cards: {len(previous_card_ids)}")

        # Check if this is the first run
        if not previous_card_ids:
            log_message("Initial run - importing all cards")
            # Treat all cards as new on first run
            import_new_cards(current_cards, deck_name)
            save_seen_ids(state_file, current_card_ids)
            return

        # Find new cards
        new_card_ids = set(current_card_ids) - set(previous_card_ids)

        if new_card_ids:
            new_cards = [card for card in current_cards if card["id"] in new_card_ids]
            log_message(f"Detected {len(new_cards)} new cards!")

            # Import to Anki
            import_new_cards(new_cards, deck_name)

            # Update state file
            save_seen_ids(state_file, current_card_ids)
        else:
            log_message("No new cards detected")

    except Exception as e:
        log_message(f"Error: {e}")
        import traceback
        log_message(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
