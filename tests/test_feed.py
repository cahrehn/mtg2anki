"""Tests for the phone feed builder. Run with: python -m pytest"""

import json
from urllib.parse import parse_qs, urlparse

from mtg2anki.feed import addnote_url, build_feed, tsv_file, write_if_changed
from mtg2anki.notes import build_note
from mtg2anki.state import FeedState

DECK = "Main::MTG::Avatar: The Last Airbender"

CARDS = [
    {"name": "Aang, Airbending Master", "id": "id-1", "layout": "normal"},
    {"name": "Legend of the Avatar", "id": "id-2", "layout": "saga"},
    {"name": "Sokka's Boomerang", "id": "id-3", "layout": "adventure"},
]


def notes():
    return [build_note(card, DECK) for card in CARDS]


def test_note_types_and_fields():
    regular, saga, adventure = notes()
    assert regular.note_type == "MTG Text Box"
    assert regular.fields == {"Front": "Aang, Airbending Master", "UUID": "id-1"}
    assert saga.note_type == "MTG Saga"
    assert saga.fields["Front"] == "Legend of the Avatar"
    assert adventure.note_type == "MTG Adventure"
    assert adventure.fields["Text"] == "{{c1::adventure}} {{c2::permanent}} Sokka's Boomerang"


def test_addnote_url_round_trips():
    url = addnote_url(notes()[0], "shortcuts://")
    assert url.startswith("anki://x-callback-url/addnote?")
    params = parse_qs(urlparse(url).query)
    assert params["type"] == ["MTG Text Box"]
    assert params["deck"] == [DECK]
    assert params["fldFront"] == ["Aang, Airbending Master"]
    assert params["fldUUID"] == ["id-1"]
    assert params["x-success"] == ["shortcuts://"]


def test_addnote_url_escapes_reserved_characters():
    note = build_note({"name": "Fire & Ash?", "id": "id-x", "layout": "normal"}, DECK)
    url = addnote_url(note)
    assert "Fire%20%26%20Ash%3F" in url
    assert parse_qs(urlparse(url).query)["fldFront"] == ["Fire & Ash?"]
    assert "x-success" not in url


def test_tsv_file_header_and_rows():
    lines = tsv_file(notes()[:1]).splitlines()
    assert lines[:5] == [
        "#separator:tab",
        "#html:true",
        "#notetype:MTG Text Box",
        f"#deck:{DECK}",
        "#columns:Front\tUUID",
    ]
    assert lines[5] == "Aang, Airbending Master\tid-1"


def test_sequence_numbers_are_stable_across_runs():
    state = FeedState()
    first = [state.seq_for(card["id"]) for card in CARDS]
    assert first == [1, 2, 3]

    # A later run sees the same cards plus a new one
    assert state.seq_for("id-2") == 2
    assert state.seq_for("id-4") == 4
    assert not state.is_known("id-5")


def test_state_round_trips_through_disk(tmp_path):
    path = tmp_path / "feed.json"
    state = FeedState()
    state.seq_for("id-1")
    state.save(path)

    reloaded = FeedState.load(path)
    assert reloaded.is_known("id-1")
    assert reloaded.seq_for("id-2") == 2


def test_build_feed_shape():
    entries = list(zip([1, 2, 3], CARDS, notes()))
    feed = build_feed({"code": "tla", "name": "Avatar"}, DECK, entries, "shortcuts://")

    assert feed["latest_seq"] == 3
    assert feed["count"] == 3
    assert set(feed["tsv_headers"]) == {"MTG Text Box", "MTG Saga", "MTG Adventure"}
    card = feed["cards"][0]
    assert card["seq"] == 1
    assert card["name"] == "Aang, Airbending Master"
    assert card["url"].startswith("anki://")
    assert card["tsv"] == "Aang, Airbending Master\tid-1"
    json.dumps(feed)  # must be serialisable


def test_write_if_changed_skips_identical_content(tmp_path):
    path = tmp_path / "current.json"
    assert write_if_changed(path, "hello", lambda _: None) is True
    assert write_if_changed(path, "hello", lambda _: None) is False
    assert write_if_changed(path, "goodbye", lambda _: None) is True
    assert path.read_text() == "goodbye"
