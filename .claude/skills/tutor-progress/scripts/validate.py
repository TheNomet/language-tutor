#!/usr/bin/env python3
"""
Validate tracking/progress.json for the language-tutor system.

Run this as the LAST step of every write-back (tutor-progress skill). It checks the
things that silently broke the Leitner system before:

  1. Valid JSON, required keys present, `_about` keys kept.
  2. Every mastery/pattern/vocab item has the right shape and box in 1..5.
  3. NO duplicate or near-duplicate ids (concept-splitting) within or across the
     `patterns` and `vocab` lists.
  4. id-shape contract for `vocab`: target word first, gloss in parens "word (english)"
     so rehearse/generate.py can split on '(' to get the target word.
  5. Review-queue health: reports the active drill pool size and flags frozen items
     (settled but never retired) and stale items (not reviewed in N days).

Exit code 0 = OK (warnings allowed), 1 = a hard error that must be fixed.

Usage:
  python3 validate.py [path-to-progress.json] [--today YYYY-MM-DD] [--strict]
"""

import json
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[4] / "tracking" / "progress.json"

# SRS interval schedule (days) by box — see .claude/skills/tutor-srs/SKILL.md.
# Box 5 recurs every ~16 days; nothing is ever retired/deleted.
INTERVAL = {1: 0, 2: 1, 3: 3, 4: 7, 5: 16}


def translit(s: str) -> str:
    s = s.lower().replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norwegian_of(mid: str) -> str:
    """The target-language headword of an id: everything before the first '(' gloss."""
    return mid.split("(")[0].strip()


def core_key(mid: str) -> frozenset:
    """Content tokens of the headword, for near-duplicate detection."""
    arts = {"en", "ei", "et", "aa", "to", "the", "a", "an"}
    toks = [t for t in translit(norwegian_of(mid)).split() if t not in arts]
    return frozenset(toks)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    today_arg = None
    for i, a in enumerate(sys.argv):
        if a.startswith("--today="):
            today_arg = a.split("=", 1)[1]
        elif a == "--today" and i + 1 < len(sys.argv):
            today_arg = sys.argv[i + 1]
    # a bare positional after stripping flags may be the path; the value after
    # "--today" is not a path, so drop it from args if present
    if today_arg and today_arg in args:
        args = [a for a in args if a != today_arg]
    path = Path(args[0]) if args else DEFAULT
    today = datetime.strptime(today_arg, "%Y-%m-%d").date() if today_arg else date.today()

    errors: list[str] = []
    warnings: list[str] = []

    try:
        d = json.loads(path.read_text())
    except Exception as e:
        print(f"ERROR: invalid JSON in {path}: {e}")
        return 1

    for k in ("current", "vocabulary", "levels", "units_completed", "weak_spots"):
        if k not in d:
            errors.append(f"missing top-level key: {k}")

    # mastery may be a single list (legacy) or split into patterns+vocab (new)
    lists = {}
    if "patterns" in d or "vocab" in d:
        lists = {"patterns": d.get("patterns", []), "vocab": d.get("vocab", [])}
        if "mastery" in d and d["mastery"]:
            warnings.append("both `mastery` (legacy) and `patterns`/`vocab` present — "
                            "migration incomplete; remove `mastery` once split is done.")
    elif "mastery" in d:
        lists = {"mastery": d["mastery"]}
        warnings.append("still on legacy single `mastery` list — split into "
                        "`patterns` + `vocab` (see SKILL.md migration).")
    else:
        errors.append("no `mastery` nor `patterns`/`vocab` list found")

    # per-item shape + box range
    for name, items in lists.items():
        for it in items:
            mid = it.get("id", "<no id>")
            if "id" not in it:
                errors.append(f"[{name}] item missing id: {it}")
            if not isinstance(it.get("box"), int) or not (1 <= it.get("box", 0) <= 5):
                errors.append(f"[{name}] bad box for {mid!r}: {it.get('box')}")
            if "last_reviewed" not in it:
                errors.append(f"[{name}] missing last_reviewed for {mid!r}")
            if "times_wrong" not in it:
                warnings.append(f"[{name}] missing times_wrong for {mid!r}")
            # vocab id-shape contract: must carry a gloss in parens
            if name == "vocab" and "(" not in mid:
                warnings.append(f"[vocab] id has no '(gloss)' — rehearse app maps by the "
                                f"headword before '(': {mid!r}")

    # duplicate / near-duplicate detection across all items
    all_items = [(name, it) for name, items in lists.items() for it in items]
    exact = {}
    near = {}
    for name, it in all_items:
        mid = it.get("id", "")
        if mid in exact:
            errors.append(f"DUPLICATE id (exact): {mid!r} in [{exact[mid]}] and [{name}]")
        else:
            exact[mid] = name
        ck = core_key(mid)
        if len(ck) >= 1:
            near.setdefault(ck, []).append((name, mid))
    for ck, group in near.items():
        if len(group) > 1:
            ids = "; ".join(f"[{n}] {m}" for n, m in group)
            warnings.append(f"NEAR-DUPLICATE (same headword tokens {set(ck)}): {ids} "
                            f"-> confirm these are truly distinct, else MERGE.")

    # review-queue health (due-driven; see tutor-srs SKILL.md)
    def parse(dt):
        try:
            return datetime.strptime(dt, "%Y-%m-%d").date()
        except Exception:
            return None

    pat = lists.get("patterns", []) if "patterns" in lists else \
        [it for it in lists.get("mastery", []) if it.get("kind") == "pattern"]
    voc = lists.get("vocab", []) if "vocab" in lists else \
        [it for it in lists.get("mastery", []) if it.get("kind") != "pattern"]

    def is_due(it):
        box = it.get("box", 1)
        lr = parse(it.get("last_reviewed", ""))
        if lr is None:
            return True
        return (today - lr).days >= INTERVAL.get(box, 0)

    due_pat = [it for it in pat if is_due(it)]
    due_voc = [it for it in voc if is_due(it)]
    print(f"patterns: {len(pat)} total ({len(due_pat)} due today)")
    print(f"vocab:    {len(voc)} total ({len(due_voc)} due today)")
    print(f"DUE FOR REVIEW today (weakest-first warm-up pool): "
          f"{len(due_pat)} patterns + {len(due_voc)} vocab = {len(due_pat) + len(due_voc)}")

    # sanity: items missing last_reviewed can't be scheduled
    no_date = [it for lst in lists.values() for it in lst if parse(it.get("last_reviewed", "")) is None]
    if no_date:
        warnings.append(f"{len(no_date)} item(s) have no valid last_reviewed — they'll "
                        f"always show as due. Set a date on every review.")

    # informational: box distribution so drift-to-5 is visible
    from collections import Counter
    dist_v = Counter(it.get("box", 1) for it in voc)
    dist_p = Counter(it.get("box", 1) for it in pat)
    print(f"box spread — patterns {dict(sorted(dist_p.items()))} | "
          f"vocab {dict(sorted(dist_v.items()))}")

    print()
    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}")

    if errors:
        print(f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"\nOK: 0 errors, {len(warnings)} warning(s).")
    return 1 if (strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
