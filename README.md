# mtg2anki

Automated workflow for importing Magic: The Gathering cards from Scryfall into Anki to help prepare for limited.

## Overview

This toolset monitors Scryfall for new card releases and automatically imports them into Anki.

## Components

### 1. scryfall-checker.sh

A bash script that periodically checks Scryfall for new cards in a specified set.

**Features:**
- Fetches cards from Scryfall API based on configurable set code and filters
- Compares results with previous run to detect new cards
- Triggers Anki import automatically when new cards are detected
- Logs all activity to `card-monitor.log`

**Configuration:**
```bash
SET_CODE="tla"  # Change this to your target set
```

**Usage:**
```bash
./scryfall-checker.sh
```

Set up with cron/launchd to run periodically for automated monitoring.

### 2. tsv2anki.scpt

An AppleScript that automates the Anki import process.

**What it does:**
1. Opens Anki
2. Triggers the import dialog (Cmd+Shift+I)
3. Opens file dialog (Cmd+G)
4. Types the TSV file path
5. Selects the correct Note Type ("MTG Text Box")

**Configuration:**
Edit the `tsvPath` variable at the top:
```applescript
set tsvPath to "/Users/username/mtg2anki/tla.tsv"
```


## Workflow

1. **Automated Monitoring**: Run `scryfall-checker.sh` periodically (e.g., via cron) to check for new cards
2. **Auto-Import**: When new cards are detected, `tsv2anki.scpt` automatically imports them into Anki

## Setup

### Prerequisites
- `jq` for JSON parsing: `brew install jq`
- Python 3 with `requests`: `pip install requests`

### Initial Setup
1. Clone or download this repository
2. Update configuration variables in each script for your environment
3. Make scripts executable: `chmod +x scryfall-checker.sh`
4. Test each component individually before setting up automation

### Automation (Optional)
Set up `scryfall-checker.sh` to run periodically using launchd or cron:

```bash
# Example crontab entry (runs every 6 hours)
0 */6 * * * /Users/cahrehn/mtg2anki/scryfall-checker.sh
```

## File Structure

```
mtg2anki/
├── scryfall-checker.sh      # Scryfall monitoring script
├── tsv2anki.scpt            # Anki import automation
├── {set}.tsv                # Current card data (e.g., tla.tsv)
├── {set}.tsv.previous       # Previous card data for comparison
└── card-monitor.log         # Activity log
```

## Notes

- The TSV format expected by Anki should match your "MTG Text Box" note type fields
- Scryfall queries can be customized in `scryfall-checker.sh` (see commented examples)
