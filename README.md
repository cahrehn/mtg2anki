# mtg2anki

Automated workflow for importing Magic: The Gathering cards from Scryfall into Anki to help prepare for limited.

## Overview

This tool monitors Scryfall for new card releases and imports them into Anki.
There are two ways to run it:

- **Desktop** — `scryfall_to_anki.py` pushes new cards straight into a running
  Anki via AnkiConnect.
- **Phone** — `build_feed.py` publishes the same cards as a JSON feed that an
  iPhone Shortcut feeds to AnkiMobile. See **[docs/iphone.md](docs/iphone.md)**.

Both share the Scryfall query, the note type mapping and the deck naming, so
the cards come out identical either way.

## scryfall_to_anki.py

Monitors Scryfall for new cards and imports them directly into Anki.

**Features:**
- Fetches cards from Scryfall API based on configurable set code
- Filters for commons/uncommons, excluding basics and DFCs
- Detects new cards by comparing with previous runs
- Imports directly to Anki via AnkiConnect
- Supports multiple card layouts: regular cards and sagas share the text box
  note type, adventures get their own
- Logs all activity to `card-monitor.log`

**Usage:**
```bash
python scryfall_to_anki.py
```

Set up with cron/launchd to run periodically for automated monitoring.

## build_feed.py

Same fetch, no Anki required. Builds every feed named in `feeds.json` (feed name
→ set code, optionally limited to a list of card names), writing for each:

- `feed/<name>.json` — every card in the set with a stable sequence number, an
  `anki://x-callback-url/addnote` URL and a text-import row
- `feed/<name>-*.tsv` — one importable text file per note type, for bulk
  seeding a new set
- `state/<name>.json` — the sequence numbers assigned so far

`current` is the feed the Shortcut reads; extra entries let you publish a second
set alongside it without disturbing it.

`.github/workflows/update-feed.yml` runs this hourly and commits the result, so
the feed stays current with no machine of yours running.

```bash
python build_feed.py
```

## Configuration

`mtg2anki/config.py`:

```python
SET_CODE = os.environ.get("MTG2ANKI_SET", "tla")  # set the desktop run imports
MTG_NOTE_TYPE = "MTG Text Box"   # regular cards and sagas
ADVENTURE_NOTE_TYPE = "MTG Adventure"
DECK_PREFIX = "Main::MTG"  # cards land in "Main::MTG::<set name>"
```

Feeds are configured in `feeds.json`, not here.

Environment overrides: `MTG2ANKI_SET` (desktop set code, and the `current`
feed's), `MTG2ANKI_DIR` (where the desktop run
keeps its state and log), `ANKICONNECT_URL`, `MTG2ANKI_X_SUCCESS`.

## Setup

### Prerequisites
- **Anki** with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on installed (desktop path only)
- **Python 3** with dependencies: `pip install -r requirements.txt`

### Initial Setup
1. Clone or download this repository
2. Install AnkiConnect in Anki (Tools → Add-ons → Get Add-ons → Code: 2055492159)
3. Install Python dependencies: `pip install -r requirements.txt`
4. Set `MTG2ANKI_SET` (or edit `mtg2anki/config.py`) for your target set
5. Ensure Anki is running when executing `scryfall_to_anki.py`

### Automation
Set up `scryfall_to_anki.py` to run periodically using launchd or cron.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Layout

```
scryfall_to_anki.py   desktop entry point (AnkiConnect)
build_feed.py         phone/CI entry point (JSON + TSV feed)
feeds.json            feed name -> set code (and optional card list)
cards/                card lists limiting a feed to named cards
mtg2anki/
  config.py           set codes, note types, deck naming, paths
  scryfall.py         Scryfall API access
  notes.py            card -> note type and fields
  ankiconnect.py      talking to desktop Anki
  feed.py             anki:// URLs, text-import files, feed JSON
  state.py            what we have already seen
  log.py              timestamped logging
```
