---
name: tutor-srs
description: The spaced-repetition (Leitner + SM-2) model for the language-tutor system — how boxes, intervals, due-dates, promotion/demotion, and retirement work, grounded in the literature. Reference for the tutor agent, the tutor-progress skill, and the rehearse app so all three behave identically. Read when changing box logic, review scheduling, or the rehearse app.
---

# Spaced repetition model (the single source of truth)

All three surfaces — the **tutor** (warm-ups), the **`tutor-progress`** skill
(write-back), and the **rehearse app** — must implement the SAME box logic. This page
is that shared spec, grounded in the literature so the numbers aren't invented.

## Literature basis

- **Leitner system (Sebastian Leitner, 1972).** Cards live in numbered boxes; each
  higher box is reviewed at a *longer interval*. Correct → promote one box; **wrong →
  back to box 1** (the retention-favoring variant, vs. the softer "back one box").
  Cards are never deleted — a high box just means "review rarely." A card only leaves
  the cycle after it survives the whole ladder.
  > Source: en.wikipedia.org/wiki/Leitner_system (original partitions 1,2,5,8,14 cm →
  > increasing intervals).
- **SM-2 (Woźniak, SuperMemo 1987; the algorithm Anki/Mnemosyne adapted).** Tracks an
  inter-repetition **interval I in days**; review is **due-driven**: show a card only
  when `last_review + I ≤ today`. First success I=1 day, second I=6 days, then I grows.
  **Fail → I resets to 1 day and the repetition count resets.** Nothing is removed;
  hard items simply recur often, easy ones rarely.
  > Source: en.wikipedia.org/wiki/SuperMemo (SM-2 pseudocode).

The key correction to our old system: **boxes are review INTERVALS, not a "done" flag.**
Box 5 does **not** mean "gone forever" — it means "review roughly every ~16 days." A
slip on any box sends the item back to box 1. That is the forgetting-safety valve.

## Our model: 5 boxes, box-derived intervals

We keep 5 Leitner boxes and derive each item's review interval from its box (no per-item
EF — simpler, faithful, easy to hand-inspect):

| Box | Interval | Meaning |
|-----|----------|---------|
| 1 | **0 days** (every session) | new, or just failed — drill now |
| 2 | **1 day** | shaky |
| 3 | **3 days** | getting there |
| 4 | **7 days** | solid |
| 5 | **16 days** (then recurs, never retires) | well known, low frequency |

This curve approximates SM-2's 1 → 6 → ~15 → ~30 progression, compressed to 5 discrete
boxes and a daily-study cadence.

### Transitions (identical everywhere)

- **Correct / confident** → `box = min(5, box + 1)`; set `last_reviewed = today`.
- **Wrong / hesitant** → `box = 1`, `times_wrong += 1`; set `last_reviewed = today`.
  (Full reset to box 1, per Leitner's retention variant + SM-2's fail rule — NOT "back
  one box." The old rehearse app did `box-1`; that was wrong and is fixed.)

### "Due" — what a review session pulls

An item is **due** when `today >= last_reviewed + interval(box)`. Sessions (tutor
warm-ups and the app's default review) draw from **due items, weakest first**
(lowest box, then most `times_wrong`, then oldest `last_reviewed`).

- Box-1 items are due every day (interval 0).
- A box-5 item is due ~16 days after its last review — it reappears, it isn't gone.
- If an item isn't due yet, it's simply not shown this session (but "All words" /
  practice-anything modes may still show it on demand).

## Retirement vs. due-ness (don't confuse them)

- **Due-ness** (above) schedules *when* an item recurs. Everything recurs eventually.
- **Active-pool trimming** is a separate, softer idea used only to keep the tutor's
  *warm-up* focus tight: settled **vocab** (box ≥ 4) is low-priority for the scarce
  ~10 warm-up slots, but it still becomes due on its interval and still appears in the
  app. **Grammar patterns never trim** — they stay eligible whenever due.
- Nothing is ever *deleted*. "Retire" only ever means "low review frequency."

## Rehearse app modes (which one touches the boxes)

The app has two focus modes that differ only in **selection** — both grade into the
same local box buffer, and Export sends it all:
- **Due for review** — the SRS mode. Shows only *due* items (weakest-weighted).
- **Even** — practice mode. Shows every word (category-filtered), ignoring due-dates.

Independently, the **answer mode** decides *what* is asked of a word:
- **Write** — English prompt → type the **citation form only** (strict: an inflected
  form does NOT count; you must type the dictionary/citation form, not an inflected one).
- **Full forms** — quiz **every** form of the word one at a time (noun: 4 forms; verb:
  4 tenses; adjective: 3). One input box; Enter checks the shown form and advances to the
  next. The word counts as **known only if ALL forms are correct** (box +1); any single
  miss resets the whole word to box 1. This is how you certify a word as fully mastered.
- **Listen & write** — dictation of the citation form (strict, same as Write).
- **Flashcard** — target-language word shown, self-rate recall.

In every mode, grading updates the box (correct → +1, wrong → reset to 1) and
`last_reviewed`. Even can promote an item not strictly "due" — accepted as a
simplicity trade-off; the next due-date is always computed from the latest review.

## Applies to both lists

`progress.json` holds `patterns` (grammar) and `vocab` (words). The box/interval/due
rules are identical for both. Item shape stays:
`{ "id": "...", "box": 1-5, "last_reviewed": "YYYY-MM-DD", "times_wrong": N }`.
`last_reviewed` is what makes due-dates work — always set it on every review.

## Shared constants (keep in sync)

Interval table, in days, indexed by box: `{1:0, 2:1, 3:3, 4:7, 5:16}`.
Demotion: wrong → box 1. Promotion: correct → box+1 (max 5).
These exact values live in: this doc, `tutor-progress/scripts/validate.py`,
`rehearse/generate.py` / `rehearse.html`, and are referenced by the tutor agent.
Change them here first, then propagate.
