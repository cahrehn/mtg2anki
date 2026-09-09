# mtg2anki

Automated workflow for importing Magic: The Gathering cards from Scryfall into Anki to help prepare for limited.

## Overview

This tool monitors Scryfall for new card releases and automatically imports them into Anki via AnkiConnect.

## scryfall_to_anki.py

Main script that monitors Scryfall for new cards and imports them directly into Anki.

**Features:**
- Fetches cards from Scryfall API based on a configurable set code
- Filters for commons/uncommons, excluding basic lands
- Imports only cards not yet successfully imported, so failures retry on the next run
- Imports directly to Anki via AnkiConnect
- Supports multiple card layouts: regular cards, sagas, adventures, prepare, and double-faced cards
- Retries transient Scryfall failures, and exits cleanly if Anki isn't running
- Logs all activity to `card-monitor.log`

**Configuration:**

The monitored set lives in `config.toml`:

```toml
set = "fra"
```

Change that one line each time a new set starts spoiling. Note types are constants near the top of `scryfall_to_anki.py` and only need editing if you rename them in Anki.

**Usage:**
```bash
python scryfall_to_anki.py
```

Each set tracks its own progress in `<set>_state.json`, so pointing `config.toml` at an older set picks up where that set left off rather than starting over.

If `config.toml` is missing or has no `set`, the script exits with an error rather than guessing — that way a typo can't silently import the wrong set.

Set up with cron/launchd to run periodically for automated monitoring.

## Setup

### Prerequisites
- **Anki** with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on installed
- **Python 3.11+** (uses the stdlib `tomllib`) with dependencies: `pip install -r requirements.txt`
- Note types matching the names in `scryfall_to_anki.py` — see [mtg-anki-templates](https://github.com/cahrehn/mtg-anki-templates)

### Initial Setup
1. Clone or download this repository
2. Install AnkiConnect in Anki (Tools → Add-ons → Get Add-ons → Code: 2055492159)
3. Install Python dependencies: `pip install -r requirements.txt`
4. Set your target set in `config.toml`
5. Ensure Anki is running when executing scripts

### Automation
Set up `scryfall_to_anki.py` to run periodically using launchd or cron:
