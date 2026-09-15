#!/usr/bin/env python3
"""
Merge rehearse-app progress back into tracking/progress.json.

The rehearse app (rehearse/rehearse.html) tracks its own Leitner state in the browser
and exports it via the "Export progress" button as rehearse-progress-YYYY-MM-DD.json:

  { "exported_on": "...", "source": "rehearse-app",
    "items": [ { "answer": "en lue", "box": 3, "last_reviewed": "2026-07-29" }, ... ] }

This script matches each exported answer to a progress.json item (patterns/vocab) by
Norwegian core-token overlap, and applies the review whose `last_reviewed` is MORE
RECENT (app vs. file wins by date). It never deletes items and never lowers a box for
an older review. Follows the SRS model in .claude/skills/tutor-srs/SKILL.md.

Usage:
  python3 merge_rehearse.py <export.json>            # dry run: show what would change
  python3 merge_rehearse.py <export.json> --write     # apply
  python3 merge_rehearse.py <export.json> --write --progress /path/to/progress.json
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

DEFAULT_PROGRESS = Path(__file__).resolve().parents[4] / "tracking" / "progress.json"
ARTICLES = {"en", "ei", "et", "å", "aa", "to", "the", "a", "an"}


def translit(s: str) -> str:
    s = s.lower().replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def core_tokens(s: str) -> set:
    return {t for t in translit(s.split("(")[0]).split() if t not in ARTICLES}


def find_item(answer: str, items: list) -> dict | None:
    """Best vocab item for an app answer, requiring a confident (not merely overlapping)
    match so distinct words don't collide (e.g. 'hvor' must not match 'hvor mange').
    Prefer: exact token-set equality > answer tokens ⊆ item tokens > highest overlap
    that covers ALL the answer's tokens."""
    want = core_tokens(answer)
    if not want:
        return None
    exact, subset, best, best_score = None, None, None, 0
    for it in items:
        toks = core_tokens(it["id"])
        if not toks:
            continue
        if want == toks and exact is None:
            exact = it
        # answer fully contained in the item's headword tokens (e.g. app 'en lue'
        # -> item 'en lue / luer / luene')
        if want <= toks and subset is None:
            subset = it
        score = len(want & toks)
        if score > best_score and want <= toks:
            best, best_score = it, score
    return exact or subset or best


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: merge_rehearse.py <export.json> [--write] [--progress PATH]")
        return 1
    export_path = Path(args[0])
    write = "--write" in sys.argv
    prog_path = DEFAULT_PROGRESS
    if "--progress" in sys.argv:
        prog_path = Path(sys.argv[sys.argv.index("--progress") + 1])

    export = json.loads(export_path.read_text())
    prog = json.loads(prog_path.read_text())
    # The rehearse app only quizzes VOCABULARY, never grammar patterns — so merges
    # only ever match/create in `vocab`. Patterns are tutor-owned and must not be
    # promoted/demoted by app practice (that caused question-word collisions).
    vocab = prog.setdefault("vocab", [])
    items = vocab
    if not vocab and "mastery" in prog:
        items = prog["mastery"]
        vocab = prog["mastery"]  # legacy: create into mastery

    changes, unmatched, created, skipped = [], [], [], []
    for row in export.get("items", []):
        answer = row.get("answer", "")
        app_box = row.get("box")
        app_date = row.get("last_reviewed", "")
        # skip rows never actually reviewed (empty date) — nothing to merge
        if not app_date:
            skipped.append(answer)
            continue
        it = find_item(answer, items)
        if it is None:
            # AUTO-CREATE a vocab item so app practice on an untracked vault word is
            # promoted into real tracking (correct id shape: "norwegian (english)").
            # Guard against the pre-fix buggy export where a month's en was another
            # month (e.g. answer "februar" with en "januar").
            en = (row.get("en") or "").strip()
            if answer.strip().lower() == en.lower() or (en and en.isalpha() and en.lower() in {
                "januar","februar","mars","april","mai","juni","juli","august",
                "september","oktober","november","desember"} and answer.lower() != en.lower()):
                skipped.append(f"{answer} (bad en='{en}')")
                continue
            new_id = f"{answer} ({en})" if en else f"{answer} (—)"
            new_item = {
                "id": new_id,
                "box": app_box,
                "last_reviewed": app_date,
                "times_wrong": 0,
            }
            vocab.append(new_item)   # items IS vocab, so this also grows the match pool
            created.append(new_item)
            continue
        cur_date = it.get("last_reviewed", "")
        # more recent review wins; ties keep the file
        if app_date and app_date > cur_date:
            if it.get("box") != app_box or cur_date != app_date:
                changes.append((it, it.get("box"), cur_date, app_box, app_date))
                if write:
                    it["box"] = app_box
                    it["last_reviewed"] = app_date

    print(f"matched {len(changes)}  created {len(created)}  skipped {len(skipped)}  "
          f"/ {len(export.get('items', []))} exported items")
    if created:
        print(f"\n{'CREATED' if write else 'WOULD CREATE'} {len(created)} new vocab item(s):")
        for it in created:
            print(f"  + {it['id'][:55]:55}  box {it['box']}  {it['last_reviewed']}")
    if changes:
        print(f"\n{'APPLIED' if write else 'WOULD CHANGE'} {len(changes)} item(s):")
        for it, ob, od, nb, nd in changes:
            print(f"  {it['id'][:55]:55}  box {ob}->{nb}  {od or '-'} -> {nd}")
    if not changes and not created:
        print("\nno changes (app has nothing newer than progress.json)")
    if skipped:
        print(f"\nskipped (no review date, or bad export row): {len(skipped)} — "
              + "; ".join(skipped[:8]))
    if unmatched:
        print(f"\nunmatched: {len(unmatched)} — " + "; ".join(unmatched[:8]))

    if write:
        prog_path.write_text(json.dumps(prog, ensure_ascii=False, indent=2) + "\n")
        print(f"\nWROTE {prog_path}")
        print("Now run validate.py and regenerate the app:")
        print("  python3 .claude/skills/tutor-progress/scripts/validate.py")
        print("  python3 rehearse/generate.py")
    else:
        print("\n(dry run — re-run with --write to apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
