#!/usr/bin/env python3
"""
Scryfall to phone feed builder

Fetches the same cards as scryfall_to_anki.py, but instead of talking to a
running Anki it writes feed/current.json - a list of every card in the set with
a stable sequence number, an AnkiMobile anki:// add-note URL, and a text-import
row. An iPhone Shortcut reads that file and adds anything newer than the last
sequence number it imported. See docs/iphone.md.

Runs anywhere (GitHub Actions, a Mac, a-Shell on iOS); needs no Anki.
"""

import re

from mtg2anki import config, scryfall
from mtg2anki.feed import build_feed, tsv_file, write_if_changed, write_json_if_changed
from mtg2anki.log import make_logger
from mtg2anki.notes import build_note
from mtg2anki.state import FeedState

log_message = make_logger()


def slug(note_type):
    return re.sub(r"[^a-z0-9]+", "-", note_type.lower()).strip("-")


def write_tsv_files(entries, log):
    """One importable text file per note type, for bulk seeding a fresh set"""
    by_note_type = {}
    for _, _, note in entries:
        by_note_type.setdefault(note.note_type, []).append(note)

    written = set()
    for note_type, notes in by_note_type.items():
        path = config.FEED_DIR / f"current-{slug(note_type)}.tsv"
        written.add(path)
        write_if_changed(path, tsv_file(notes), log)

    # Drop files for note types this set no longer has
    for path in config.FEED_DIR.glob("current-*.tsv"):
        if path not in written:
            path.unlink()
            log(f"Removed {path.name}")


def main():
    log_message("=" * 60)
    set_code = config.SET_CODE
    log_message(f"Building feed for set '{set_code}'")

    set_info = scryfall.fetch_set_info(set_code)
    deck = config.deck_name(set_info["name"])
    log_message(f"Set: '{set_info['name']}' ({set_code})")
    log_message(f"Target deck: {deck}")

    cards = scryfall.fetch_cards(set_code, log_message)

    state_path = config.feed_state_file()
    state = FeedState.load(state_path)
    new_count = sum(1 for card in cards if not state.is_known(card["id"]))

    entries = [(state.seq_for(card["id"]), card, build_note(card, deck)) for card in cards]
    entries.sort(key=lambda entry: entry[0])

    feed = build_feed(set_info, deck, entries, config.X_SUCCESS_URL)
    log_message(f"{len(cards)} cards, {new_count} new, latest sequence {feed['latest_seq']}")

    changed = write_json_if_changed(config.FEED_DIR / "current.json", feed, log_message)
    write_tsv_files(entries, log_message)
    state.save(state_path)

    if not changed:
        log_message("Feed unchanged")


if __name__ == "__main__":
    main()
