#!/usr/bin/env python3
"""
Build vocab.js for the rehearsal app.

Sources (all read-only):
  - Obsidian grammar "forms" references  -> full inflection for nouns/verbs/adjectives
  - Obsidian unit notes "Words" tables    -> the remaining word classes
                                             (conjunctions, question/quantity/time words, ...)
  - tracking/progress.json                 -> Leitner box per item (drives review order)

Output: rehearse/vocab.js  (a `const VOCAB = [...]` so the app loads from file:// with no server)

>>> LANGUAGE NOTE <<<
This parser was written for Norwegian and still assumes Norwegian conventions:
it classifies words by leading article (en/ei/et -> noun, "å " -> verb) and reads
tense columns labelled infinitive/present/preteritum/perfektum. If your target
language differs, adapt the parsing helpers below (see parse_forms_file /
parse_unit_words and the ARTICLES/tense-label logic) to match how the tutor-obsidian
skill lays out YOUR forms references. Until then the rehearse app is optional — the
tutor's own warm-up already drives spaced repetition from progress.json.
"""


import json
import os
import re
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Vault location: read from tracking/profile.json ("vault_path"), or the VAULT_PATH env
# var. No path is hardcoded — it works on macOS/Windows/Linux once vault_path is set by
# the tutor-setup skill.
def _resolve_vault() -> Path:
    env = os.environ.get("VAULT_PATH")
    if env:
        return Path(env).expanduser()
    try:
        prof = json.loads((REPO / "tracking" / "profile.json").read_text())
        vp = prof.get("vault_path", "")
        if vp and not vp.startswith("TODO"):
            return Path(vp).expanduser()
    except Exception:
        pass
    raise SystemExit(
        "No vault path. Set profile.json 'vault_path' (run tutor-setup) or export "
        "VAULT_PATH=/path/to/your/Obsidian/LanguageFolder"
    )

VAULT = _resolve_vault()
GRAMMAR = VAULT / "grammar"
OUT = REPO / "rehearse" / "vocab.js"

# ---------------------------------------------------------------- helpers


def clean_note(s: str) -> str:
    s = re.sub(r"`snd:[^`]*`", "", s)
    s = s.replace("**", "").replace("*", "").replace("`", "")
    s = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", s)  # [[a|b]] -> b
    return re.sub(r"\s+", " ", s).strip()


def strip_snd(cell: str) -> str:
    """Remove `snd:...` audio-slug backtick tokens and markdown, keep the words."""
    cell = re.sub(r"`snd:[^`]*`", "", cell)
    cell = cell.replace("`", "").replace("*", "").replace("**", "")
    return cell.strip()


def translit(s: str) -> str:
    """Norwegian -> ascii key for fuzzy matching (æ->ae ø->oe å->aa)."""
    s = s.lower()
    s = s.replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    # also fold any stray accents
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


ARTICLES = {"en", "ei", "et", "å", "aa", "to"}


def core_tokens(no_form: str) -> list[str]:
    """Content words of a Norwegian form, articles dropped, transliterated."""
    toks = translit(no_form).split()
    return [t for t in toks if t not in ARTICLES]


def parse_alternates(cell: str) -> list[str]:
    """
    Turn a display cell like 'kona (konen)' or 'lille / små' or 'vann (et)'
    into the list of real word variants a learner might type.
    """
    cell = strip_snd(cell)
    variants: list[str] = []
    # split on slash first (kvart over / på, lille / små)
    for part in cell.split("/"):
        part = part.strip()
        if not part:
            continue
        # a parenthetical alternate: 'kona (konen)' -> 'kona', 'konen'
        m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", part)
        if m:
            main = m.group(1).strip()
            inside = m.group(2).strip()
            if main:
                variants.append(main)
            # only treat as a word if it looks like one (not 'et', 'both accepted' etc.)
            if inside and re.match(r"^[a-zæøåA-ZÆØÅ ]+$", inside) and inside not in (
                "et",
                "en",
                "ei",
            ):
                variants.append(inside)
            elif inside in ("et", "en", "ei"):
                # gender hint like 'vann (et)' -> keep the word, prepend article variant
                variants.append(f"{inside} {main}")
        else:
            variants.append(part)
    # dedupe, keep order
    seen = set()
    out = []
    for v in variants:
        v = v.strip()
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def md_rows(text: str, header_start: str):
    """Yield lists-of-cells for each data row in a markdown table under a `##` heading."""
    rows = []
    lines = text.splitlines()
    i = 0
    in_table = False
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # separator row like |---|---|
            if all(re.match(r"^:?-{2,}:?$", c) or c == "" for c in cells if c):
                in_table = True
                i += 1
                continue
            if in_table:
                rows.append(cells)
        else:
            in_table = False
        i += 1
    return rows


# ---------------------------------------------------------------- boxes

boxes: dict[str, tuple[int, int, str]] = {}  # core-token-string -> (box, times_wrong, last_reviewed)


def load_boxes():
    prog = json.loads((REPO / "tracking" / "progress.json").read_text())
    # New shape: two lists `patterns` + `vocab`. Legacy: single `mastery`.
    items = prog.get("patterns", []) + prog.get("vocab", [])
    if not items:
        items = prog.get("mastery", [])
    for item in items:
        mid = item["id"]
        # the Norwegian part is before the '(' gloss
        no_part = mid.split("(")[0]
        key = translit(no_part)
        if key:
            boxes[key] = (item.get("box", 3), item.get("times_wrong", 0),
                          item.get("last_reviewed", ""))


def lookup_box(no_forms: list[str]) -> tuple[int, int, str]:
    """Find the best Leitner box for an entry by matching its core tokens to mastery ids."""
    wanted = set()
    for f in no_forms:
        wanted.update(core_tokens(f))
    if not wanted:
        return (3, 0, "")
    best = None
    for key, val in boxes.items():
        ktoks = set(key.split())
        if wanted & ktoks:
            # prefer the lowest box (weakest) among matches -> review harder items more
            if best is None or val[0] < best[0]:
                best = val
    return best if best else (3, 0, "")


# ---------------------------------------------------------------- parsers

entries: list[dict] = []
seen_cores: set[str] = set()
all_accepted: set[str] = set()  # every accepted word-form across all entries (for dedup)


def core_key(citation: str) -> str:
    # use only the FIRST word variant (headword), slugs stripped, so that
    # 'en skjorte / skjorter' and the forms-file 'en skjorte' collapse together
    alts = parse_alternates(citation)
    head = alts[0] if alts else strip_snd(citation)
    toks = core_tokens(head)
    return " ".join(toks)


def add_entry(cat, en, forms, note="", unit=""):
    """forms: list of (label, norwegian_display). First is the citation form."""
    citation = forms[0][1]
    ckey = core_key(citation)
    if ckey and ckey in seen_cores:
        return  # avoid duplicates across sources
    if ckey:
        seen_cores.add(ckey)
    accept = set()
    tts = []  # (label, spoken norwegian) for the reveal panel
    for label, disp in forms:
        for v in parse_alternates(disp):
            accept.add(v.lower())
            # accept without leading article too
            toks = v.split()
            if len(toks) > 1 and toks[0].lower() in ARTICLES:
                accept.add(" ".join(toks[1:]).lower())
        tts.append({"label": label, "no": strip_snd(disp)})
    box, wrong, last_reviewed = lookup_box([f[1] for f in forms])
    all_accepted.update(accept)
    entries.append(
        {
            "cat": cat,
            "en": en.strip(),
            "answer": strip_snd(citation),
            "accept": sorted(accept),
            "forms": tts,
            "note": clean_note(note),
            "box": box,
            "wrong": wrong,
            "last_reviewed": last_reviewed,
            "unit": unit,
        }
    )


def parse_nouns():
    text = (GRAMMAR / "g1.1-noun-forms.md").read_text()
    for cells in md_rows(text, "noun"):
        if len(cells) < 3:
            continue
        en = cells[0]
        if en.lower() in ("english", ""):
            continue
        indef_sg = cells[1]
        def_sg = cells[2] if len(cells) > 2 else ""
        indef_pl = cells[3] if len(cells) > 3 else ""
        def_pl = cells[4] if len(cells) > 4 else ""
        forms = [("a / an (indef. sg.)", indef_sg)]
        if def_sg:
            forms.append(("the (def. sg.)", def_sg))
        if indef_pl:
            forms.append(("plural (indef.)", indef_pl))
        if def_pl:
            forms.append(("the plural (def.)", def_pl))
        add_entry("noun", en, forms)


def parse_verbs():
    text = (GRAMMAR / "g0.3-verb-forms.md").read_text()
    for cells in md_rows(text, "verb"):
        if len(cells) < 2:
            continue
        en = cells[0]
        if en.lower() in ("english", ""):
            continue
        # modal table: English | presens | note
        header_is_modal = False
        inf = cells[1]
        # detect: infinitive forms start with 'å'
        if strip_snd(inf).startswith("å") or strip_snd(inf).startswith("aa"):
            forms = [("infinitive (å …)", inf)]
            if len(cells) > 2 and cells[2]:
                forms.append(("present (nå)", cells[2]))
            if len(cells) > 3 and cells[3]:
                forms.append(("past (preteritum)", cells[3]))
            if len(cells) > 4 and cells[4]:
                forms.append(("perfect (har …)", cells[4]))
            add_entry("verb", en, forms)
        else:
            # modal: just a present form
            add_entry("verb", en, [("present", inf)], note="modal verb")


def parse_adjectives():
    text = (GRAMMAR / "g2.5-adjective-forms.md").read_text()
    for cells in md_rows(text, "adj"):
        if len(cells) < 3:
            continue
        en = cells[0]
        low = en.lower()
        if low in ("english", "form", ""):
            continue
        # skip the 'liten' mini-table (columns: form | use | example) and any prose row:
        # a real adjective form is a single word, so bail if the base cell is a phrase.
        if "`" in en or "snd:" in en:
            continue
        base = cells[1]
        base_clean = strip_snd(base)
        if not base_clean or " " in base_clean or "," in base_clean:
            continue
        t_form = cells[2] if len(cells) > 2 else ""
        e_form = cells[3] if len(cells) > 3 else ""
        note = cells[4] if len(cells) > 4 else ""
        forms = [("base (en-word)", base)]
        if t_form and strip_snd(t_form) != strip_snd(base):
            forms.append(("-t (et-word)", t_form))
        if e_form:
            forms.append(("-e (def./plural)", e_form))
        add_entry("adj", en, forms, note=note)


UNIT_FILES = [
    "unit-1.1.md",
    "unit-1.2.md",
    "unit-1.3.md",
    "unit-1.4.md",
    "unit-1.5.md",
    "unit-1.6.md",
    "unit-2.4.md",
]


def parse_unit_words():
    """Pick up word classes not in the forms files (conjunctions, q-words, quantity, time)."""
    for fn in UNIT_FILES:
        text = (VAULT / fn).read_text()
        unit = fn.replace("unit-", "").replace(".md", "")
        # only the "## Words" section, not "## Verbs"
        m = re.search(r"##\s*Words\s*\n(.*?)(?:\n##\s|\Z)", text, re.S)
        if not m:
            continue
        # Only the real vocab table (proper 'English | Norwegian | note' header),
        # which sits BEFORE any '###' subsection. Everything after the first '###'
        # (Numbers / Days / Months / Round-numbers grids) is a borderless DISPLAY
        # grid with an empty header — layout, not vocab — so stop there.
        block = re.split(r"\n###\s", m.group(1))[0]
        for cells in md_rows(block, "words"):
            if len(cells) < 2:
                continue
            en, no = cells[0], cells[1]
            if en.lower() in ("english", ""):
                continue
            # extra guard: skip any borderless grid rows that start with a digit
            if re.match(r"^\d", en.strip()) or re.match(r"^\d", strip_snd(no)):
                continue
            note = cells[2] if len(cells) > 2 else ""
            # dedup: already captured (with full inflection) if any variant is accepted
            variants = [v.lower() for v in parse_alternates(no)]
            if any(v in all_accepted for v in variants):
                continue
            ckey = core_key(no)
            if ckey and ckey in seen_cores:
                continue
            # classify by leading article so filters work (en/ei/et -> noun, å -> verb)
            head = parse_alternates(no)[0] if parse_alternates(no) else no
            first = translit(head).split()[0] if translit(head) else ""
            cat = "word"
            if first in ("en", "ei", "et"):
                cat = "noun"
            elif first in ("aa",):
                cat = "verb"
            add_entry(cat, en, [("", no)], note=note, unit=unit)


NUMBERS = [
    ("1", "en / ett"), ("2", "to"), ("3", "tre"), ("4", "fire"), ("5", "fem"),
    ("6", "seks"), ("7", "sju / syv"), ("8", "åtte"), ("9", "ni"), ("10", "ti"),
    ("11", "elleve"), ("12", "tolv"), ("13", "tretten"), ("14", "fjorten"),
    ("15", "femten"), ("16", "seksten"), ("17", "sytten"), ("18", "atten"),
    ("19", "nitten"),
    # tens
    ("20", "tjue"), ("30", "tretti"), ("40", "førti"), ("50", "femti"),
    ("60", "seksti"), ("70", "sytti"), ("80", "åtti"), ("90", "nitti"),
    ("100", "hundre"),
]

ORDINALS = [
    ("1st", "første"), ("2nd", "andre"), ("3rd", "tredje"), ("4th", "fjerde"),
    ("5th", "femte"), ("6th", "sjette"), ("7th", "sjuende"), ("8th", "åttende"),
    ("9th", "niende"), ("10th", "tiende"), ("11th", "ellevende"), ("12th", "tolvte"),
    ("13th", "trettende"), ("14th", "fjortende"), ("15th", "femtende"),
    ("16th", "sekstende"), ("17th", "syttende"), ("18th", "attende"),
    ("19th", "nittende"), ("20th", "tjuende"),
]


def add_numbers():
    for en, no in NUMBERS:
        add_entry("word", f"number {en}", [("", no)], note="number", unit="1.6")
    for en, no in ORDINALS:
        add_entry("word", f"ordinal {en}", [("", no)],
                  note="ordinal (numeral + period = ordinal, e.g. 3. = tredje)", unit="1.6")


# Days & months are listed as borderless DISPLAY grids in unit-1.6 (not vocab tables),
# so parse_unit_words skips them. Add them explicitly here (English prompt -> Norwegian),
# same as numbers. Boxes still come from progress.json via lookup_box in add_entry.
DAYS = [
    ("Monday", "mandag"), ("Tuesday", "tirsdag"), ("Wednesday", "onsdag"),
    ("Thursday", "torsdag"), ("Friday", "fredag"), ("Saturday", "lørdag"),
    ("Sunday", "søndag"),
]
MONTHS = [
    ("January", "januar"), ("February", "februar"), ("March", "mars"),
    ("April", "april"), ("May", "mai"), ("June", "juni"), ("July", "juli"),
    ("August", "august"), ("September", "september"), ("October", "oktober"),
    ("November", "november"), ("December", "desember"),
]


def add_days_months():
    for en, no in DAYS:
        add_entry("word", en, [("", no)], note="day of the week (lowercase)", unit="1.6")
    for en, no in MONTHS:
        add_entry("word", en, [("", no)], note="month (lowercase)", unit="1.6")


# ---------------------------------------------------------------- main

def main():
    load_boxes()
    parse_nouns()
    parse_verbs()
    parse_adjectives()
    parse_unit_words()
    add_numbers()
    add_days_months()

    # stable, useful ordering: weakest boxes first, then by category
    entries.sort(key=lambda e: (e["box"], -e["wrong"], e["cat"], e["en"]))

    banner = (
        "// AUTO-GENERATED by generate.py — do not edit by hand.\n"
        "// Source: Obsidian forms references + unit notes + progress.json boxes.\n"
    )
    OUT.write_text(banner + "const VOCAB = " + json.dumps(entries, ensure_ascii=False, indent=2) + ";\n")
    # small summary
    from collections import Counter
    cats = Counter(e["cat"] for e in entries)
    print(f"Wrote {len(entries)} items to {OUT}")
    print("By category:", dict(cats))
    print("Box spread:", dict(Counter(e["box"] for e in entries)))


if __name__ == "__main__":
    main()
