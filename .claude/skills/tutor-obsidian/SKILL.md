---
name: tutor-obsidian
description: Owns the Obsidian vault write-back for the learner's study — the grammar book (grammar/), per-unit vocabulary notes (unit-X.Y.md), and the forms references (nouns / adjectives / verbs, as the target language needs). Use whenever a grammar point is taught or clarified, or a new word is introduced, to record it in the vault. Keeps grammar and vocabulary separated, one-rule-one-home, with sourced citations.
---

# tutor-obsidian — the vault write-back

This skill owns the learner's review material in their Obsidian vault (kept in sync so it
reaches their phone). The tutor delegates all vault edits here.

**Vault root.** Read the absolute path from `tracking/profile.json` → `vault_path`. That
folder IS the Obsidian vault (it has its own `.obsidian/`). Never hardcode a path here;
always read `vault_path`. If it's missing or still a `TODO` placeholder, the repo isn't
set up — run `tutor-setup` first.

Three layers, kept strictly separated — **no exercises, no session chatter**, just
vocabulary + grammar + forms:

## 1. Grammar book — `grammar/`

Rules live **here only**, never inline in a unit note. One rule, one home.

- Find the matching `g<unit>-<topic>.md` (word-order, nouns-and-gender, plurals,
  pronouns, possessives, adjectives, negation, cases, tenses, subordinate-clauses… —
  whatever systems the target language has). If none fits, create `g<unit>-<topic>.md`
  — prefix with the unit number where the topic is introduced so files sort in
  curriculum order — and add it to `grammar-index.md` under the right category.
- Write for someone who wants the **mental model**: the type system, tables, short
  decision trees, 1–2 real target-language examples. Keep explanations tight. Don't
  duplicate an existing rule; link to it instead. (If the learner's profile says they
  dislike code blocks / pseudo-code, avoid them.)
- **Verify uncertain grammar** against the sources listed in `grammar-index.md` (the
  authoritative online grammar, dictionary, and language-council site the setup skill
  recorded for this language). When you confirm a rule from a source, add a short
  `> Source:` note beneath it. If a correction turns out wrong (the learner pushes back
  with reason), fix the page and note it.

## 2. Unit note — `unit-X.Y.md`

The unit's **vocabulary** + links to grammar. Create from `_template.md` if missing
(fill id/title, link in `index.md`).

- **Grammar covered:** a short list of `[[…]]` wikilinks into the grammar book for the
  rules this unit touched, targeting the exact heading where useful
  (e.g. `[[g2.5-adjectives#Agreement]]`). No inline rules.
- **Words table** (`English | Target language | note`): append new vocabulary. English
  first so the learner can cover the target column and translate. Put gender/article and
  irregular forms in the target cell. Keep verbs OUT of this table.
- **Verbs table** (`English | citation form | + the tenses the language marks`): verbs
  here, conjugated. Fill tenses taught; leave a cell blank until introduced.
- Obsidian `[[…]]` links; tidy and skimmable.

## 3. Forms references — `grammar/` (the "everything by word type" home)

For **every new word**, add a row to the matching reference (in addition to the unit
note above). Create the references the target language actually needs — typically:

- **Nouns** → `g<unit>-noun-forms.md`: the full paradigm row (all number/definiteness/
  case forms the language marks), under its declension pattern.
- **Adjectives** → `g<unit>-adjective-forms.md`: all agreement forms, placed **next to
  its opposite/pair** where one exists (big↔small, wet↔dry, old↔new).
- **Verbs** → `g<unit>-verb-forms.md`: all tenses/forms (bold = strong/irregular),
  grouped thematically with **pair verbs together** (fetch↔deliver, ask↔answer).

These are paradigm references, not word banks — fine for them to grow. Linked at the top
of `grammar-index.md` under "Forms references".

## Audio

To add click-to-hear pronunciation for new forms, use the **`tutor-pronunciation`**
skill — it owns the TTS fetch, slugging, and embed syntax. Keep slugs consistent with
existing rows (transliterate diacritics, spaces→`-`, lowercase).

## Consistency with tracking

Every new word is recorded **twice**: here (unit note + forms reference) and as a
`vocab` item in `progress.json` (via the `tutor-progress` skill). Grammar points get a
`patterns` item there. Keep the two in sync — same session, both updated.
