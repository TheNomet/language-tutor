---
name: tutor-setup
description: First-run bootstrap for a fresh copy of this language-tutor template. Use ONCE, at the very beginning, when tracking/profile.json or curriculum/plan.md still contain TODO/<placeholder> text — it interviews the learner, fills in their profile and learning plan for the chosen language, creates the Obsidian vault (grammar book, index, template, forms references), sets the TTS language + grammar sources, and runs the validator. Do not use once the repo is already set up.
---

# tutor-setup — bootstrap a fresh copy

Run this **once** to turn the blank template into a working tutor for one learner and one
target language. Detect "needs setup" when `tracking/profile.json` still has `TODO` values
or `curriculum/plan.md` still has `<TARGET LANGUAGE>` placeholders.

Work through the steps in order. Keep it conversational and brief — one small batch of
questions at a time, not a wall. Confirm before writing files.

## Step 1 — Interview

Ask (in the learner's base language), in ~3 batches:

**Who + why**
- Name; native/strong language(s) (used for explanations).
- Target language (and variety/dialect if it matters, e.g. Bokmål vs Nynorsk, European
  vs Latin-American Spanish).
- Primary motivation / goal. Is there a specific exam or certification (name + target
  CEFR level)? Or practical fluency only?
- Self-assessed current level (rough CEFR is fine).

**Real life (so examples land)**
- Where they live; how much they're exposed to / already use the language.
- Their #1 real-world situation for the language (this becomes Unit 1.7).
- People/topics they talk about; 4–6 contexts to rotate examples through.
- How they like to learn (rules & tables vs examples-first; any dislikes, e.g. no code
  blocks). Tone preference (blunt vs encouraging).

**Logistics**
- Study frequency, any deadline, device(s).
- Do they use Obsidian already? Where is their vault (or should one be created)?

## Step 2 — Fill `tracking/profile.json`

Replace every `TODO` with their answers. Set:
- `native_languages`, `target_language`, `lesson_language`, `current_level`, `history`,
  `primary_motivation`, `living_situation`, `practical_context`, `expected_difficulties`,
  `constraints`.
- `preferences` — adjust the defaults to their tone/correction taste (keep the inline
  `~~wrong~~ **right**` correction contract unless they object).
- `tts_lang` — the Google-TTS code for the target language (no, de, es, fr, it, pt, nl,
  sv, pl, …).
- `grammar_sources` — 2–3 authoritative references for THIS language. Pick real ones,
  e.g.:
  - Norwegian: NTNU "Norwegian on the Web" (ntnu.edu/web/now), ordbokene.no, sprakradet.no
  - German: canoonet/Duden (duden.de), DWDS (dwds.de)
  - Spanish: RAE (rae.es), Wikilengua
  - French: Le Bon Usage / Larousse, CNRTL (cnrtl.fr)
  If unsure, search for the language's authoritative grammar + a major dictionary +
  (if any) its language-council/standard body, and confirm the URLs resolve.

## Step 3 — Rewrite `curriculum/plan.md` for the language

Keep the stage/unit/checkpoint **structure**; replace placeholders with grammar that
**actually exists** in the target language. Do NOT invent features it lacks and DO add
ones the skeleton omits:
- Only include gender/case/aspect/tone/definiteness systems the language has.
- Order units so each grammar system is introduced before it's combined.
- Make Unit 1.7 the learner's #1 real situation (from Step 1).
- Fill the exam milestones only if they have an exam goal; otherwise soften ⭐ markers to
  plain level milestones.
- Delete the template blockquote at the top when done.

Verify any grammar claims you're unsure of against the `grammar_sources` before writing.

## Step 4 — Create the Obsidian vault

Decide the vault path with the learner. Default (iCloud-synced, reaches phone):
`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/<VaultName>/<LanguageFolder>/`
The `<LanguageFolder>` itself is the Obsidian vault (it gets its own `.obsidian/`). If
they already have a vault, create a `<LanguageFolder>` inside it instead.

Write the absolute path into `profile.json` → `vault_path`, then create:

- `<vault>/index.md` — links to `grammar/grammar-index.md` and (as they're created) each
  `unit-X.Y.md`.
- `<vault>/_template.md` — the shape of a unit note (see `tutor-obsidian`): a "Grammar
  covered" wikilink list, a Words table (`English | Target | note`), and a Verbs table
  (`English | citation | + the tenses this language marks`).
- `<vault>/grammar/grammar-index.md` — a map with sections: **Forms references** (links
  to the noun/adjective/verb forms files, created lazily as words appear) and one section
  per grammar category. Put the chosen `grammar_sources` at the top under "Sources".
- `<vault>/grammar/g0.0-glossary.md` — shared grammar terms, also in the target language.
- `<vault>/audio/` folder (for `tutor-pronunciation`).

Keep grammar rules in `grammar/` only; vocabulary in unit notes. (Full contract lives in
the `tutor-obsidian` skill — follow it for all later edits.)

To make inline audio buttons look clean, optionally tell them about the small Obsidian
audio plugin/CSS snippet described in `tutor-pronunciation` (not required to start).

## Step 5 — Point tooling at the vault

- `rehearse/generate.py`: set the `VAULT` path near the top to the same `vault_path`
  (replace the `/CHANGE-ME/...` placeholder).
- Leave `tracking/progress.json` as the empty scaffold — the first session fills it. Set
  `current.unit` to the first unit of the freshly-written plan and
  `vocabulary.baseline_known_estimate` to a rough guess of words they already know.

## Step 6 — Validate & hand off

- Run `python3 .claude/skills/tutor-progress/scripts/validate.py --today <today>` — fix
  any ERROR.
- Confirm `profile.json` and `plan.md` have no leftover `TODO`/`<...>` placeholders.
- Tell the learner setup is done and that next time they just say "run today's session".
  Then either start Session 1 or stop, per their preference.

Do not run `tutor-setup` again after this; ongoing sessions use `tutor-progress` and
`tutor-obsidian`.
