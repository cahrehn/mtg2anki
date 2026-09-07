"""Tests for the phone feed builder. Run with: python -m pytest"""

import json
from urllib.parse import parse_qs, urlparse

from mtg2anki import config, scryfall
from mtg2anki.feed import (
    addnote_url,
    build_feed,
    load_card_list,
    select_cards,
    tsv_file,
    write_if_changed,
)
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


def test_search_query_excludes_alchemy_rebalances():
    query = scryfall.search_query("dmu")
    assert "set:dmu" in query
    assert "-is:rebalanced" in query  # else A-Radha ships alongside Radha
    assert "-type:basic" in query
    assert "-is:dfc" in query
    assert "r<r" in query


def test_note_types_and_fields():
    regular, saga, adventure = notes()
    assert regular.note_type == "MTG Text Box"
    assert regular.fields == {"Front": "Aang, Airbending Master", "UUID": "id-1"}
    # Sagas are plain text box notes; the template handles the occlusion
    assert saga.note_type == "MTG Text Box"
    assert saga.fields == {"Front": "Legend of the Avatar", "UUID": "id-2"}
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
    assert set(feed["tsv_headers"]) == {"MTG Text Box", "MTG Adventure"}
    card = feed["cards"][0]
    assert card["seq"] == 1
    assert card["name"] == "Aang, Airbending Master"
    assert card["url"].startswith("anki://")
    assert card["tsv"] == "Aang, Airbending Master\tid-1"
    json.dumps(feed)  # must be serialisable


def test_feeds_are_read_from_feeds_json(monkeypatch, tmp_path):
    feeds_file = tmp_path / "feeds.json"
    feeds_file.write_text(
        '{"current": "tla", "dmu": {"set": "dmu", "cards": "cards/dmu.txt"}}'
    )
    monkeypatch.setattr(config, "FEEDS_FILE", feeds_file)

    monkeypatch.delenv("MTG2ANKI_SET", raising=False)
    specs = config.feeds()
    assert specs["current"] == {"set": "tla", "cards": None}
    assert specs["dmu"]["set"] == "dmu"
    assert specs["dmu"]["cards"] == config.REPO_DIR / "cards/dmu.txt"

    # The env override only redirects the main feed
    monkeypatch.setenv("MTG2ANKI_SET", "blb")
    assert config.feeds()["current"]["set"] == "blb"
    assert config.feeds()["dmu"]["set"] == "dmu"


def test_card_list_skips_comments_blanks_and_repeats(tmp_path):
    path = tmp_path / "dmu.txt"
    path.write_text("# a comment\n\nCut Down\n  Impulse  \nCut Down\n")
    assert load_card_list(path) == ["Cut Down", "Impulse"]


def test_select_cards_follows_list_order_and_reports_misses():
    pool = [
        {"name": "Impulse", "id": "id-a", "layout": "normal"},
        {"name": "Cut Down", "id": "id-b", "layout": "normal"},
        {"name": "Bite Down", "id": "id-c", "layout": "normal"},
    ]
    selected, missing = select_cards(pool, ["Cut Down", "impulse", "Shivan Dragon"])

    # List order wins over Scryfall order, so a win-rate sorted list imports best first
    assert [card["name"] for card in selected] == ["Cut Down", "Impulse"]
    assert missing == ["Shivan Dragon"]


def test_missing_names_surface_in_the_feed():
    entries = list(zip([1], CARDS[:1], notes()[:1]))
    feed = build_feed({"code": "dmu"}, DECK, entries, None, ["Shivan Dragon"])
    assert feed["missing"] == ["Shivan Dragon"]
    assert "missing" not in build_feed({"code": "dmu"}, DECK, entries, None, [])


def test_each_feed_keeps_its_own_state(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "FEED_STATE_DIR", tmp_path)
    assert config.feed_state_file("current") != config.feed_state_file("dmu")

    current, dmu = FeedState(), FeedState()
    current.seq_for("id-1")
    # A second feed numbers from 1 again rather than continuing the first
    assert dmu.seq_for("id-9") == 1


def test_write_if_changed_skips_identical_content(tmp_path):
    path = tmp_path / "current.json"
    assert write_if_changed(path, "hello", lambda _: None) is True
    assert write_if_changed(path, "hello", lambda _: None) is False
    assert write_if_changed(path, "goodbye", lambda _: None) is True
    assert path.read_text() == "goodbye"
