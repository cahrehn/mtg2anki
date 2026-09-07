"""Building the feed the phone consumes: anki:// URLs and text-import rows."""

import json
from urllib.parse import quote

ADDNOTE_BASE = "anki://x-callback-url/addnote"


def addnote_url(note, x_success=None):
    """AnkiMobile x-callback-url that adds this note.

    Opening it from Shortcuts adds the note to the named note type and deck
    without any import dialog. x_success (e.g. "shortcuts://") sends control
    back to the caller so a loop can keep going.
    """
    params = [("type", note.note_type), ("deck", note.deck)]
    params += [(f"fld{name}", value) for name, value in note.fields.items()]
    if x_success:
        params.append(("x-success", x_success))
    query = "&".join(f"{quote(key, safe='')}={quote(value, safe='')}" for key, value in params)
    return f"{ADDNOTE_BASE}?{query}"


def tsv_row(note):
    """Field values as one tab separated line for Anki's text file import"""
    return "\t".join(value.replace("\t", " ") for value in note.fields.values())


def tsv_header(note):
    """Anki file header pinning note type, deck and column mapping"""
    return "\n".join([
        "#separator:tab",
        "#html:true",
        f"#notetype:{note.note_type}",
        f"#deck:{note.deck}",
        "#columns:" + "\t".join(note.fields.keys()),
    ])


def tsv_file(notes):
    """A complete importable text file for notes that share a note type"""
    return tsv_header(notes[0]) + "\n" + "\n".join(tsv_row(note) for note in notes) + "\n"


def load_card_list(path):
    """Card names from a list file, in order. Blank lines and # comments skipped."""
    names = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            if line not in names:
                names.append(line)
    return names


def select_cards(cards, names):
    """Keep only the named cards, in the order the list gives them.

    Returns (selected, missing). Matching ignores case, but the feed carries
    Scryfall's spelling. Ordering by the list means a list sorted by win rate
    imports its best cards first.
    """
    by_name = {card["name"].casefold(): card for card in cards}
    selected, missing = [], []
    for name in names:
        card = by_name.get(name.casefold())
        if card:
            selected.append(card)
        else:
            missing.append(name)
    return selected, missing


def build_feed(set_info, deck, entries, x_success=None, missing=None):
    """The JSON the phone reads.

    entries is a list of (seq, card, note) tuples, oldest sequence first.
    """
    cards = [
        {
            "seq": seq,
            "id": card["id"],
            "name": card["name"],
            "layout": card.get("layout", "normal"),
            "note_type": note.note_type,
            "deck": note.deck,
            "fields": note.fields,
            "url": addnote_url(note, x_success),
            "tsv": tsv_row(note),
        }
        for seq, card, note in entries
    ]
    headers = {}
    for _, _, note in entries:
        headers.setdefault(note.note_type, tsv_header(note))

    feed = {
        "set": set_info,
        "deck": deck,
        "count": len(cards),
        "latest_seq": max((card["seq"] for card in cards), default=0),
        "tsv_headers": headers,
        "cards": cards,
    }
    if missing:
        # Names in the card list Scryfall didn't return, so they are visible
        # from the phone without digging through CI logs
        feed["missing"] = missing
    return feed


def write_if_changed(path, content, log=print):
    """Write only on a real change, so the hourly CI run does not churn commits"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == content:
        return False
    path.write_text(content)
    log(f"Wrote {path.name}")
    return True


def write_json_if_changed(path, data, log=print):
    return write_if_changed(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n", log)
