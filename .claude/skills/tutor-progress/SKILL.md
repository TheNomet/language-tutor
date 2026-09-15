---
name: tutor-progress
description: Owns all write-back to the learner's tracking files — tracking/progress.json (Leitner boxes, patterns/vocab, weak_spots, streak, vocabulary pace log) and tracking/log.md. Use at the END of every tutoring session, or whenever updating boxes, adding a mastered word/pattern, recording a mistake, advancing a unit, or maintaining progress. Enforces dedup, the id contract, and retirement so the review queue stays healthy.
---

# tutor-progress — the tracking write-back

This skill owns `tracking/progress.json` and `tracking/log.md`. The tutor delegates all
bookkeeping here so the Leitner data stays clean. Free-handed edits are what corrupt it
(duplicate items, nothing retiring) — follow these rules instead.

Base dir: this skill's folder. Scripts live in `scripts/`.
Progress file: `tracking/progress.json` (repo root). Log: `tracking/log.md`.

## The two Leitner lists

`progress.json` holds **two** spaced-repetition lists:

- **`patterns`** — grammar systems / fault lines (word order, agreement, negation
  placement, cases, verb conjugation classes…). These are what you actually re-drill.
  They **never fully retire** (cap at box 5 but stay eligible for warm-ups).
- **`vocab`** — individual words. id shape **`"target-word (english gloss)"`** — the
  target-language word first, gloss in parens — because `rehearse/generate.py` splits on
  `(` to read the target word. Vocab **retires** from the active pool once settled (see
  below); it stays in the file and in the Obsidian forms references for reference.

Item shape (both lists):
`{ "id": "...", "box": 2, "last_reviewed": "2026-07-28", "times_wrong": 0 }`

## Leitner update rules (per item practiced this session)

The SRS model (boxes, intervals, due-dates) is specified in
**`.claude/skills/tutor-srs/SKILL.md`** — read it; it's the source of truth and the
rehearse app + tutor follow the same rules. Summary:

1. Find the item. **Search first** (see dedup) — is this concept already tracked?
2. If it isn't in the right list, add it at `box: 1`, `times_wrong: 0`.
3. Correct / confident → `box = min(5, box + 1)`.
4. Wrong / hesitant → `box = 1` (full reset, per Leitner/SM-2), `times_wrong + 1`.
5. Always set `last_reviewed` to today — due-dates depend on it.

## Review scheduling (due-driven)

Interval by box (days): **{1:0, 2:1, 3:3, 4:7, 5:16}**. An item is **due** when
`today >= last_reviewed + interval(box)`. Warm-ups draw from **due items, weakest first**
(lowest box → most `times_wrong` → oldest `last_reviewed`). Box 5 is **not** retired — it
recurs ~every 16 days; a slip drops it to box 1. Nothing is ever deleted.

To keep the tutor's ~10 warm-up slots focused, settled **vocab** (box ≥ 4) is
low-priority even when due; **grammar patterns** are always eligible when due.

## Dedup — the rule that is easy to break (do NOT split concepts)

Before adding ANY item, search both lists for one covering the same concept. If found,
**UPDATE that row** — never create a parallel one. One concept = one row, forever.

- Same grammar idea worded differently → update the existing row (you may refine its
  `id` text, but keep it one row and preserve its history).
- A word you already track → update, don't re-add.
- If a new nuance is genuinely distinct, it may be its own row — but the validator will
  flag it as a near-duplicate; confirm it's truly distinct.

## Retirement (keeps the warm-up queue usable)

Retirement here means **low review frequency, never deletion** — see the SRS spec for
the full model. Practically:

- A **vocab** item at `box >= 4` is low-priority for the tutor's scarce warm-up slots,
  but it still becomes **due** on its interval (box 4 = 7 days, box 5 = 16 days) and
  still appears in the rehearse app. It never leaves the file.
- **patterns** are always eligible when due; they don't get deprioritised.
- Nothing is ever removed. If the due pool feels too big, that's the schedule catching
  up — items spread out as their boxes climb through real reviews.

## weak_spots

Free-text recurring problems with `{id, status, note}`. Add new ones; **remove** ones
the learner has clearly mastered (don't let them pile up). Status ladder:
`new → observed → improving → resolved` (delete when resolved and stable).

## The `current` block + vocabulary pace

- `current.last_session_on` = today. Set `started_on` if null.
- `current.sessions_completed += 1`.
- `current.day_streak`: +1 if last session was yesterday; reset to 1 if a day skipped.
- `current.mode` / `current.notes`: append a dated one-line note for future-you.
- **Unit advance:** when a unit's goals are met without heavy help, add it to
  `units_completed` and set `current.unit` to the next unit in `plan.md` (never invent
  units). **Level-ups** (`reached_A1/A2/B1`) only after the plan's checkpoint/mock.
- **Vocabulary pace:** append `{date, session, new_words, note}` to
  `vocabulary.session_log` (count only words produced ≥2×), and add that count to
  `vocabulary.new_words_introduced_in_program`. Check the running pace vs the
  daily/weekly target and tell the tutor whether to nudge next session up or down.

## log.md

Append ONE entry at the bottom, format at the top of the file:
practiced / went well / struggled with / brought back next time / tutor note (+ aloud
mission). Human-readable story; the structured data lives in progress.json.

## ALWAYS validate before you finish

Run the validator; fix every ERROR (warnings are advisory):

```
python3 .claude/skills/tutor-progress/scripts/validate.py --today <YYYY-MM-DD>
```

It checks: valid JSON + required keys; box in 1..5; item shape; **exact + near-duplicate
ids**; the vocab id `(gloss)` contract; and reports the active-pool size + frozen/stale
items. Keep JSON valid (no trailing commas, UTF-8, keep `_about` keys).

## Rehearse app sync (scripts/)

- **`validate.py`** — the health check above; run every session.
- **`merge_rehearse.py`** — folds the rehearse app's exported progress back into
  `progress.json`. When the learner has rehearsed in the app and clicks **Export
  progress**, they get a `rehearse-progress-*.json`; run
  `python3 .claude/skills/tutor-progress/scripts/merge_rehearse.py <that file>`
  (dry-run first, then `--write`). It matches by target-word token overlap and applies
  the **more recent review** (app vs. file). If an exported word has **no**
  progress.json item, it **auto-creates** a `vocab` item so that practice is promoted
  into real tracking. This closes the loop so app practice counts.

After any structural change (big cleanup, merge), regenerate the rehearse app so it
re-seeds from the merged truth: `python3 rehearse/generate.py`.
