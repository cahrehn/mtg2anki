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

1. Make sure Actions is enabled for the repo (Settings → Actions → General →
   "Allow all actions").
2. Set the set code in `feeds.json` (see [Feeds](#feeds) below). It ships with
   `tla`, so there's nothing to do until you switch sets.
3. Get a feed built — see [Testing before you merge](#testing-before-you-merge)
   if the branch isn't merged yet, otherwise Actions → "Update card feed" → Run
   workflow, or just wait for the hourly schedule. It commits
   `feed/current.json` and `state/feed.json`.
4. Build the Shortcut below.

The feed lives at:

```
https://raw.githubusercontent.com/cahrehn/mtg2anki/main/feed/current.json
```

## Testing before you merge

GitHub has a catch here: **`schedule` and the "Run workflow" button only exist
for workflow files that are on the default branch.** Until this is merged,
Actions shows nothing to click, even though the file is there on the branch.

`push` triggers have no such restriction, so the workflow also runs on any push
to a `claude/**` branch that touches `build_feed.py`, `mtg2anki/`, `tests/` or
the workflow itself. It commits the feed back to *that branch*, so you get a
real end-to-end test — real Scryfall data, real feed, real Shortcut run —
without merging anything.

While testing, point the Shortcut at the branch:

```
https://raw.githubusercontent.com/cahrehn/mtg2anki/claude/mobile-script-anki-import-ye9ptr/feed/current.json
```

(the unambiguous form, if a branch name with slashes ever confuses something, is
`.../mtg2anki/refs/heads/<branch>/feed/current.json` — both work.)

Swap the branch for `main` after merging. To
kick off a run without a code change, edit any file in the branch from the
GitHub web UI (the pencil icon works fine on a phone) and commit — e.g. add a
line to this file.

Two things worth knowing while testing:

- Sequence numbers are assigned once and committed to `state/feed.json`. If you
  test on the branch and then merge, the numbers carry over — the phone cursor
  stays valid. If you'd rather start clean, delete `state/feed.json` and the
  next run renumbers from 1.
- The `.tsv` files and `feed/current.json` are committed by the bot, so merging
  the branch brings that data along with it.

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

## Feeds

`feeds.json` maps a feed name to a set code:

```json
{
  "current": "tla",
  "dmu": "dmu"
}
```

Every entry gets built into `feed/<name>.json`, `feed/<name>-*.tsv` and its own
`state/<name>.json`. Editing this file is all it takes to switch sets or to
publish a second one — and it's editable from a phone in the GitHub web UI,
which is why it lives here rather than in a repo variable. A push to it also
triggers the workflow on `claude/**` branches.

Names are yours to pick; `current` is only special in that it's the one the
Shortcut points at and the one `MTG2ANKI_SET` overrides.

**Changing sets:** point `current` at the new set code. Sequence numbers restart
at 1 for a feed the first time it sees a set, so reset the phone cursor to `0`
when you switch — a set change is exactly when you *want* the whole set to come
in. The deck name follows the set name from Scryfall (`Main::MTG::<set name>`).

**A second feed** is the safe way to try things: it has its own sequence
numbering and its own deck, so nothing you do with it can disturb the set
you're actually following. The `dmu` entry is there as a test target —
Dominaria United lands in `Main::MTG::Dominaria United`, which you can delete
in one go afterwards. Point the Shortcut at
`.../feed/dmu.json` and a separate cursor file to try the whole loop without
touching your real deck. Drop the entry from `feeds.json` when you're done
(the generated files stay until you delete them).

### Overriding without editing the file

`MTG2ANKI_SET` — as a repository variable (Settings → Secrets and variables →
Actions → Variables, or <https://github.com/cahrehn/mtg2anki/settings/variables/actions>)
or as a workflow_dispatch input — redirects the `current` feed to a different
set code without touching `feeds.json`. It's a *variable*, not a secret; the
value shows in run logs, which is fine for a set code.

## Running the fetch somewhere other than Actions

`build_feed.py` needs nothing but `requests` and writes into the repo, so it also
runs from the Mac (`python build_feed.py`) or from [a-Shell](https://holzschu.github.io/a-Shell_iOS/)
on the phone itself if you'd rather not depend on CI. Point the Shortcut at a
local file instead of the raw URL in that case.

## What GitHub Actions costs

Nothing, for this repo. Standard GitHub-hosted runners are **free with no minute
cap on public repositories** — the billed minute allowances only apply to
private repos. This job takes well under a minute, so even hourly it is noise.

Things that do apply:

- **If you ever make this repo private**, the free tier is 2,000 minutes/month
  and this workflow would burn roughly a third of it (~730 runs, billed with a
  1-minute minimum each). Drop the schedule to every few hours if you do that.
- **Scheduled workflows get disabled after 60 days of repository inactivity.**
  GitHub emails the owner and you re-enable with one click. During spoiler
  season the workflow's own commits count as activity; in the off-season expect
  to get that mail eventually.
- **Every feed in `feeds.json` is built on every run**, in one job. Two feeds is
  two or three extra Scryfall requests, not a second workflow run.
- **Cron is best-effort.** The minimum interval is 5 minutes, and scheduled runs
  are queued on shared infrastructure — they can be delayed by several minutes
  to an hour at peak times, and can be dropped entirely under heavy load. Fine
  for spoilers; don't treat the hourly cadence as a guarantee.
- **Schedules only run on the default branch**, so the hourly run starts after
  you merge.
- The other ceilings (6 hours per job, 20 concurrent jobs, 35 days of log
  retention) are nowhere near what this uses.
- Repo size grows by one commit whenever the card list changes — a few hundred
  KB across a whole spoiler season. The feed is deliberately not rewritten when
  nothing changed, so quiet hours produce no commits at all.
- Scryfall is free and has no key. The script identifies itself with a
  User-Agent and spaces out paginated requests, as their API asks. Two or three
  requests an hour is far below anything they'd care about.

## Staleness

`raw.githubusercontent.com` caches for around five minutes. If you've just run
the workflow and the feed looks old, either wait it out or point the Shortcut at
the API instead, which isn't cached:

```
https://api.github.com/repos/cahrehn/mtg2anki/contents/feed/current.json
```

with header `Accept: application/vnd.github.raw` (60 requests/hour unauthenticated).
