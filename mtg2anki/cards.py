"""Card name and layout helpers shared across scripts."""

import re

# Note types, matching the templates in mtg-anki-templates
MTG_NOTE_TYPE = "MTG Text Box"  # regular cards (and sagas)
ADVENTURE_NOTE_TYPE = "MTG Adventure"
PREPARE_NOTE_TYPE = "MTG Prepare"
DFC_NOTE_TYPE = "MTG DFC"

# Layouts that get a cloze note type rather than the plain text box
CLOZE_LAYOUTS = ("adventure", "prepare", "transform", "modal_dfc")

CLOZE_RE = re.compile(r"\{\{c\d+::(.*?)\}\}")


def extract_front_name(value):
    """Derive the card's front-face name from a note field value.

    Handles plain names (Front field) and cloze-wrapped Text fields like
    '{{c1::permanent}} {{c2::spell}} Blazing Firesinger // Seething Song'.
    17lands lists multi-face cards by front face only, so we drop the cloze
    labels and everything after ' // '.
    """
    text = re.sub(r"<[^>]+>", " ", value)   # strip HTML tags
    text = CLOZE_RE.sub("", text)           # drop {{cN::label}} wrappers
    text = text.split(" // ")[0]            # front face only
    return " ".join(text.split()).strip()


def dfc_face_names(card_name, card_faces=None):
    """Return (front, back) names for a double-faced card.

    Prefers Scryfall's card_faces, falling back to splitting the combined
    name on ' // '.
    """
    if card_faces and len(card_faces) >= 2:
        return card_faces[0].get("name", ""), card_faces[1].get("name", "")
    parts = card_name.split(" // ")
    front = parts[0] if len(parts) > 0 else ""
    back = parts[1] if len(parts) > 1 else ""
    return front, back


def note_for_layout(card_name, card_id, layout, card_faces=None):
    """Map a Scryfall layout to its Anki note type and fields."""
    if layout == "adventure":
        return ADVENTURE_NOTE_TYPE, {
            "Text": f"{{{{c1::adventure}}}} {{{{c2::permanent}}}} {card_name}",
            "UUID": card_id,
        }
    if layout == "prepare":
        return PREPARE_NOTE_TYPE, {
            "Text": f"{{{{c1::permanent}}}} {{{{c2::spell}}}} {card_name}",
            "UUID": card_id,
        }
    if layout in ("transform", "modal_dfc"):
        front_name, back_name = dfc_face_names(card_name, card_faces)
        return DFC_NOTE_TYPE, {
            "Text": f"{{{{c1::{front_name}}}}} {{{{c2::{back_name}}}}}",
            "UUID": card_id,
        }
    return MTG_NOTE_TYPE, {"Front": card_name, "UUID": card_id}
