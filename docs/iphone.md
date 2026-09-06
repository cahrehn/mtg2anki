# Running this from an iPhone

The Mac workflow is `scryfall_to_anki.py` → AnkiConnect → desktop Anki. Two of
those three don't exist on a phone, so the phone version splits the job in half:

- **GitHub Actions runs the script.** `build_feed.py` does the same Scryfall
  fetch and new-card detection, but instead of talking to Anki it publishes
  `feed/current.json` to this repo.
- **A Shortcut does the importing.** It reads that file, works out which cards
  it hasn't imported yet, and hands each one to AnkiMobile as an
  `anki://x-callback-url/addnote` URL. No import dialog, no file juggling, and
  the cards land in the right note type and deck by name.

Nothing runs on the phone except the Shortcut, so this also keeps working while
the Mac is asleep. Cards sync to AnkiWeb and back to the Mac as usual.

## Why not the other options

| Option | Verdict |
| --- | --- |
| AnkiConnect | Desktop-only add-on. There is no iOS equivalent. |
| AnkiWeb in a browser | Sync and review only — it can't import decks or files. |
| `.apkg` import | Works, but a generated `.apkg` carries its own note types. If the note type IDs don't match the ones in your collection, Anki imports them as *copies* (`MTG Text Box-a1b2c`) and your templates break. Getting those IDs needs the Mac, which defeats the point. |
| `.txt`/`.tsv` import | Genuinely works on iOS, and is the best way to bulk-seed a brand new set. It needs a file-picker round trip and a field-mapping confirmation per import, so it's clumsy for the daily 5-card spoiler trickle. See [Bulk import](#bulk-import-a-whole-set-at-once) below. |

## One-time setup

1. Merge this branch to `main` and make sure Actions is enabled for the repo
   (Settings → Actions → General → "Allow all actions").
2. Set the set code: Settings → Secrets and variables → Actions → Variables →
   new repository variable `MTG2ANKI_SET` (e.g. `tla`). Without it the workflow
   falls back to `tla`.
3. Run the workflow once by hand (Actions → "Update card feed" → Run workflow),
   or wait for the hourly schedule. It commits `feed/current.json` and
   `state/feed.json`.
4. Build the Shortcut below.

The feed lives at:

```
https://raw.githubusercontent.com/cahrehn/mtg2anki/main/feed/current.json
```

## The feed format

```jsonc
{
  "set": { "code": "tla", "name": "Avatar: The Last Airbender", "released_at": "..." },
  "deck": "Main::MTG::Avatar: The Last Airbender",
  "count": 187,
  "latest_seq": 187,
  "tsv_headers": { "MTG Text Box": "#separator:tab\n#html:true\n..." },
  "cards": [
    {
      "seq": 1,                       // stable, only ever increases
      "id": "...",                    // Scryfall ID, goes in the UUID field
      "name": "Aang, Airbending Master",
      "layout": "normal",             // normal | saga | adventure
      "note_type": "MTG Text Box",
      "deck": "Main::MTG::Avatar: The Last Airbender",
      "fields": { "Front": "...", "UUID": "..." },
      "url": "anki://x-callback-url/addnote?type=...",  // ready to open
      "tsv": "Aang, Airbending Master\tid"              // ready to import
    }
  ]
}
```

`seq` is the trick that keeps the phone honest. Every card gets a number the
first time the workflow sees it, and those numbers never change or get reused —
they keep climbing even when you switch sets. The Shortcut stores the highest
number it has imported and only opens cards above it, so nothing is tracked
per-device on this end and a failed run is fixed by editing one number.

## The Shortcut

Name it something like **MTG → Anki**. Actions in order:

1. **Get File** — Service: iCloud Drive, Path: `Shortcuts/mtg2anki-cursor.txt`,
   *Error If Not Found:* **off**.
2. **If** — `File` *has any value*
   - **Set Variable** `Cursor` to `File`
   - **Otherwise** → **Set Variable** `Cursor` to a **Text** action containing `0`
3. **Get Contents of URL** — the raw feed URL above. Set Variable `Feed`.
4. **Get Dictionary Value** — Get `Value` for key `cards` in `Feed`.
5. **Repeat with Each** (over the result of step 4):
   1. **Get Dictionary Value** — `seq` in `Repeat Item`
   2. **If** — that *is greater than* `Cursor`
      - **Get Dictionary Value** — `url` in `Repeat Item`
      - **Open URLs**
6. **Get Dictionary Value** — `latest_seq` in `Feed`
7. **Save File** — Service: iCloud Drive, Path: `Shortcuts/mtg2anki-cursor.txt`,
   *Ask Where To Save:* off, *Overwrite If File Exists:* on.
8. **Open URLs** — `anki://x-callback-url/sync` (pushes the new cards to AnkiWeb
   so the Mac picks them up).

Each `url` already carries `x-success=shortcuts://`, so AnkiMobile hands control
straight back and the loop continues to the next card. You'll see the screen
flip between Shortcuts and Anki once per card — that's the whole cost of this
approach. iOS may ask for permission to open Anki the first time; allow it.

Add it to the Home Screen, or drive it from an Automation (Settings → Automation
→ Time of Day) if you want it hands-off.

### Skipping the backlog

The first run will try to import every card in the set. If those are already in
your collection from the Mac, set the cursor first: open the feed URL in Safari,
find `latest_seq`, and save that number to
`iCloud Drive/Shortcuts/mtg2anki-cursor.txt` (a one-action Shortcut with **Text**
→ **Save File** does it). The same edit re-imports a batch if something went
wrong — just lower the number.

Duplicates are cheap to survive either way: `addnote` refuses a note whose first
field matches an existing one unless `dupes=1` is passed, which the feed
deliberately doesn't pass.

## Bulk import a whole set at once

For seeding a new set from scratch, the workflow also publishes one importable
text file per note type:

```
feed/current-mtg-text-box.tsv
feed/current-mtg-saga.tsv
feed/current-mtg-adventure.tsv
```

Each carries an Anki file header pinning the note type, deck and column mapping,
so importing is: open the raw URL in Safari → Download → Files → tap the file →
Open in AnkiMobile → confirm. Repeat per file.

Use this on an **empty** deck. On a re-import Anki matches existing notes by
first field and updates them, and these files only contain the two fields the
script sets — anything you've since filled in by hand on those notes is at risk.
For incremental updates, use the Shortcut.

## Changing sets

Change the `MTG2ANKI_SET` repository variable and run the workflow. Sequence
numbers keep counting up across sets, so the phone cursor keeps working and the
new set's cards import as normal. The deck name follows the set name from
Scryfall (`Main::MTG::<set name>`).

## Running the fetch somewhere other than Actions

`build_feed.py` needs nothing but `requests` and writes into the repo, so it also
runs from the Mac (`python build_feed.py`) or from [a-Shell](https://holzschu.github.io/a-Shell_iOS/)
on the phone itself if you'd rather not depend on CI. Point the Shortcut at a
local file instead of the raw URL in that case.

## Staleness

`raw.githubusercontent.com` caches for around five minutes. If you've just run
the workflow and the feed looks old, either wait it out or point the Shortcut at
the API instead, which isn't cached:

```
https://api.github.com/repos/cahrehn/mtg2anki/contents/feed/current.json
```

with header `Accept: application/vnd.github.raw` (60 requests/hour unauthenticated).
