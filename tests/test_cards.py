"""Tests for card name parsing and layout routing."""

import pytest

from mtg2anki.cards import (
    ADVENTURE_NOTE_TYPE,
    DFC_NOTE_TYPE,
    MTG_NOTE_TYPE,
    PREPARE_NOTE_TYPE,
    dfc_face_names,
    extract_front_name,
    note_for_layout,
)


class TestExtractFrontName:
    """extract_front_name feeds the 17lands lookup in lowwinrate.py.

    A wrong result there means a card is either silently skipped or, with
    --delete, matched against the wrong 17lands entry and deleted.
    """

    def test_plain_name_passes_through(self):
        assert extract_front_name("Lightning Bolt") == "Lightning Bolt"

    def test_strips_cloze_wrappers(self):
        value = "{{c1::permanent}} {{c2::spell}} Blazing Firesinger"
        assert extract_front_name(value) == "Blazing Firesinger"

    def test_keeps_front_face_only(self):
        value = "{{c1::Woodwork Prodigy}} {{c2::Soul Tether}}"
        # Cloze labels are dropped entirely, leaving nothing to match on
        assert extract_front_name(value) == ""

    def test_splits_on_double_slash(self):
        assert extract_front_name("Fire // Ice") == "Fire"

    def test_strips_html_tags(self):
        assert extract_front_name("<b>Lightning</b> Bolt") == "Lightning Bolt"

    def test_collapses_whitespace(self):
        assert extract_front_name("  Lightning   Bolt  ") == "Lightning Bolt"

    def test_cloze_and_double_slash_together(self):
        value = "{{c1::adventure}} {{c2::permanent}} Bonecrusher Giant // Stomp"
        assert extract_front_name(value) == "Bonecrusher Giant"

    def test_apostrophes_are_preserved(self):
        # Real card name that broke earlier name-matching attempts
        assert extract_front_name("Old Fat Spider Can't See Me") == "Old Fat Spider Can't See Me"


class TestDfcFaceNames:
    def test_prefers_card_faces(self):
        faces = [{"name": "Delver of Secrets"}, {"name": "Insectile Aberration"}]
        assert dfc_face_names("Delver of Secrets // Insectile Aberration", faces) == (
            "Delver of Secrets",
            "Insectile Aberration",
        )

    def test_falls_back_to_splitting_name(self):
        assert dfc_face_names("Front Face // Back Face") == ("Front Face", "Back Face")

    def test_single_face_leaves_back_empty(self):
        assert dfc_face_names("Lightning Bolt") == ("Lightning Bolt", "")

    def test_ignores_incomplete_card_faces(self):
        # Only one face present: fall back to the name split rather than IndexError
        assert dfc_face_names("Front // Back", [{"name": "Front"}]) == ("Front", "Back")


class TestNoteForLayout:
    """Layout routing is where the 'MTG Saga' bug lived.

    Sagas were sent to a note type that didn't exist in the collection, so
    every saga import failed. They must route to the plain text-box type.
    """

    def test_saga_uses_text_box_note_type(self):
        note_type, fields = note_for_layout("Down, Down to Goblin-town", "uuid-1", "saga")
        assert note_type == MTG_NOTE_TYPE
        assert fields == {"Front": "Down, Down to Goblin-town", "UUID": "uuid-1"}

    def test_normal_card_uses_text_box_note_type(self):
        note_type, fields = note_for_layout("Lightning Bolt", "uuid-2", "normal")
        assert note_type == MTG_NOTE_TYPE
        assert fields["Front"] == "Lightning Bolt"

    def test_unknown_layout_falls_back_to_text_box(self):
        # A layout Scryfall adds later should still import, not crash
        note_type, _ = note_for_layout("Some Card", "uuid-3", "brand_new_layout")
        assert note_type == MTG_NOTE_TYPE

    def test_adventure_uses_cloze_fields(self):
        note_type, fields = note_for_layout("Bonecrusher Giant", "uuid-4", "adventure")
        assert note_type == ADVENTURE_NOTE_TYPE
        assert fields["Text"] == "{{c1::adventure}} {{c2::permanent}} Bonecrusher Giant"
        assert "Front" not in fields

    def test_prepare_uses_cloze_fields(self):
        note_type, fields = note_for_layout("Woodwork Prodigy", "uuid-5", "prepare")
        assert note_type == PREPARE_NOTE_TYPE
        assert fields["Text"] == "{{c1::permanent}} {{c2::spell}} Woodwork Prodigy"

    @pytest.mark.parametrize("layout", ["transform", "modal_dfc"])
    def test_dfc_layouts_use_face_names(self, layout):
        faces = [{"name": "Front Face"}, {"name": "Back Face"}]
        note_type, fields = note_for_layout("Front Face // Back Face", "uuid-6", layout, faces)
        assert note_type == DFC_NOTE_TYPE
        assert fields["Text"] == "{{c1::Front Face}} {{c2::Back Face}}"

    def test_dfc_without_faces_splits_the_name(self):
        note_type, fields = note_for_layout("Front Face // Back Face", "uuid-7", "transform")
        assert note_type == DFC_NOTE_TYPE
        assert fields["Text"] == "{{c1::Front Face}} {{c2::Back Face}}"

    def test_every_layout_carries_the_uuid(self):
        # UUID drives dedupe on re-runs; a layout that drops it duplicates notes
        for layout in ["normal", "saga", "adventure", "prepare", "transform", "modal_dfc"]:
            _, fields = note_for_layout("Card // Other", "uuid-8", layout)
            assert fields["UUID"] == "uuid-8", f"{layout} dropped the UUID"
