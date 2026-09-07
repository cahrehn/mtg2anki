"""Turning a Scryfall card into the Anki note we want for it."""

from mtg2anki.config import ADVENTURE_NOTE_TYPE, MTG_NOTE_TYPE


class Note:
    """An Anki note: a note type, a deck, and ordered fields."""

    def __init__(self, note_type, deck, fields):
        self.note_type = note_type
        self.deck = deck
        self.fields = fields

    @property
    def first_field(self):
        return next(iter(self.fields.values()))


def build_note(card, deck):
    """Map a Scryfall card to the note type and fields it should be added as"""
    layout = card.get("layout", "normal")

    if layout == "adventure":
        return Note(ADVENTURE_NOTE_TYPE, deck, {
            "Text": f"{{{{c1::adventure}}}} {{{{c2::permanent}}}} {card['name']}",
            "UUID": card["id"],
        })

    # Sagas included: the MTG Text Box template works out that a card is a saga
    # and adjusts the occlusion itself, so they need no note type of their own.
    return Note(MTG_NOTE_TYPE, deck, {
        "Front": card["name"],
        "UUID": card["id"],
    })
