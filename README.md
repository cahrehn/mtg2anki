# mtg2anki

Automated workflow for importing Magic: The Gathering cards from Scryfall into Anki to help prepare for limited.

## Overview

This tool monitors Scryfall for new card releases and automatically imports them into Anki via AnkiConnect.

## scryfall_to_anki.py

Main script that monitors Scryfall for new cards and imports them directly into Anki.

**Features:**
- Fetches cards from Scryfall API based on configurable set code
- Filters for commons/uncommons, excluding basics and DFCs
- Detects new cards by comparing with previous runs
- Imports directly to Anki via AnkiConnect
- Supports multiple card layouts: regular cards, sagas, and adventures
- Logs all activity to `card-monitor.log`

**Configuration:**
```python
SET_CODE = "tla"  # Change this to your target set
MTG_NOTE_TYPE = "MTG Text Box"
SAGA_NOTE_TYPE = "MTG Saga"
ADVENTURE_NOTE_TYPE = "MTG Adventure"
```

**Usage:**
```bash
python scryfall_to_anki.py
```

Set up with cron/launchd to run periodically for automated monitoring.

## Setup

### Prerequisites
- **Anki** with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on installed
- **Python 3** with dependencies: `pip install -r requirements.txt`

### Initial Setup
1. Clone or download this repository
2. Install AnkiConnect in Anki (Tools → Add-ons → Get Add-ons → Code: 2055492159)
3. Install Python dependencies: `pip install -r requirements.txt`
4. Update `SET_CODE` in `scryfall_to_anki.py` for your target set
5. Ensure Anki is running when executing scripts

### Automation
Set up `scryfall_to_anki.py` to run periodically using launchd or cron:
