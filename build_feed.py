#!/usr/bin/env python3
"""
Scryfall to phone feed builder

Fetches the same cards as scryfall_to_anki.py, but instead of talking to a
running Anki it writes feed/<name>.json - a list of every card in the set with
a stable sequence number, an AnkiMobile anki:// add-note URL, and a text-import
row. An iPhone Shortcut reads that file and adds anything newer than the last
sequence number it imported. See docs/iphone.md.

Builds every feed named in feeds.json, so a second set can be published
alongside the main one (to try things out, or to follow two sets at once)
without disturbing it.

Runs anywhere (GitHub Actions, a Mac, a-Shell on iOS); needs no Anki.
"""

import re

from mtg2anki import config, scryfall
from mtg2anki.feed import (
    build_feed,
    load_card_list,
    select_cards,
    tsv_file,
    write_if_changed,
    write_json_if_changed,
)
from mtg2anki.log import make_logger
from mtg2anki.notes import build_note
from mtg2anki.state import FeedState

log_message = make_logger()


def slug(note_type):
    return re.sub(r"[^a-z0-9]+", "-", note_type.lower()).strip("-")


def write_tsv_files(name, entries, log):
    """One importable text file per note type, for bulk seeding a fresh set"""
    by_note_type = {}
    for _, _, note in entries:
        by_note_type.setdefault(note.note_type, []).append(note)

    written = set()
    for note_type, notes in by_note_type.items():
        path = config.FEED_DIR / f"{name}-{slug(note_type)}.tsv"
        written.add(path)
        write_if_changed(path, tsv_file(notes), log)

    # Drop files for note types this set no longer has
    for path in config.FEED_DIR.glob(f"{name}-*.tsv"):
        if path not in written:
            path.unlink()
            log(f"Removed {path.name}")


def build(name, spec, log):
    """Build one named feed"""
    set_code = spec["set"]
    log("=" * 60)
    log(f"Feed '{name}': set '{set_code}'")

    set_info = scryfall.fetch_set_info(set_code)
    deck = config.deck_name(set_info["name"])
    log(f"Set: '{set_info['name']}' ({set_code})")
    log(f"Target deck: {deck}")

    cards = scryfall.fetch_cards(set_code, log)

    missing = []
    if spec["cards"]:
        names = load_card_list(spec["cards"])
        cards, missing = select_cards(cards, names)
        log(f"Limited to {spec['cards'].name}: {len(cards)} of {len(names)} listed cards")
        for card_name in missing:
            log(f"  Not found in {set_code}: {card_name}")

    state_path = config.feed_state_file(name)
    state = FeedState.load(state_path)
    new_count = sum(1 for card in cards if not state.is_known(card["id"]))

    entries = [(state.seq_for(card["id"]), card, build_note(card, deck)) for card in cards]
    entries.sort(key=lambda entry: entry[0])

    feed = build_feed(set_info, deck, entries, config.X_SUCCESS_URL, missing)
    log(f"{len(cards)} cards, {new_count} new, latest sequence {feed['latest_seq']}")

    changed = write_json_if_changed(config.feed_file(name), feed, log)
    write_tsv_files(name, entries, log)
    state.save(state_path)

    if not changed:
        log("Feed unchanged")


def main():
    failed = []
    for name, spec in config.feeds().items():
        try:
            build(name, spec, log_message)
        except Exception as e:
            # One bad set code shouldn't stop the others from updating
            log_message(f"Feed '{name}' failed: {e}")
            failed.append(name)

    if failed:
        raise SystemExit(f"Failed to build: {', '.join(failed)}")


if __name__ == "__main__":
    main()
