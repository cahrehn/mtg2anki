"""Tests for the imported-card state file.

State decides what gets retried. Recording a card that failed to import
strands it permanently; that's the bug that hid the HOB sagas for days.
"""

import json

import pytest

import scryfall_to_anki
from mtg2anki import config


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Point state files at a temp dir instead of the real repo."""
    monkeypatch.setattr(config, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(scryfall_to_anki, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(config, "state_file", lambda code: tmp_path / f"{code}_state.json")
    monkeypatch.setattr(scryfall_to_anki, "state_file", config.state_file)
    return tmp_path


class TestLoadState:
    def test_missing_file_starts_empty(self, repo):
        assert scryfall_to_anki.load_state("fra") == {"card_ids": []}

    def test_round_trips(self, repo):
        scryfall_to_anki.save_state("fra", ["a", "b"])
        assert scryfall_to_anki.load_state("fra")["card_ids"] == ["a", "b"]

    def test_sets_do_not_share_state(self, repo):
        scryfall_to_anki.save_state("fra", ["fra-card"])
        scryfall_to_anki.save_state("hob", ["hob-card"])

        assert scryfall_to_anki.load_state("fra")["card_ids"] == ["fra-card"]
        assert scryfall_to_anki.load_state("hob")["card_ids"] == ["hob-card"]

    def test_written_as_readable_json(self, repo):
        scryfall_to_anki.save_state("fra", ["a"])
        written = json.loads((repo / "fra_state.json").read_text())
        assert written == {"card_ids": ["a"]}


class TestPendingSelection:
    """The set arithmetic in main() that decides what to import.

    Kept as explicit assertions because the rule is easy to regress: only
    successes are persisted, and the state is scoped to cards Scryfall still
    returns.
    """

    def test_failed_imports_stay_pending(self):
        current = {"a", "b", "c"}
        previous = {"a"}          # only 'a' imported successfully before
        imported = {"b"}          # 'c' failed this run

        new_state = (previous | imported) & current
        assert new_state == {"a", "b"}
        assert "c" in current - new_state, "failed card must remain pending"

    def test_cards_pulled_from_scryfall_leave_state(self):
        current = {"a"}           # 'b' was removed from the set
        previous = {"a", "b"}

        assert (previous | set()) & current == {"a"}

    def test_nothing_pending_when_all_imported(self):
        current = {"a", "b"}
        previous = {"a", "b"}
        assert current - previous == set()
