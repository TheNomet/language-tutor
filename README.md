# Language Tutor — a structured, file-based system for learning any language

A simple, durable system to learn usable everyday language and (optionally) reach a
target CEFR level for an exam or citizenship. Built for a **short daily session** (sized
by material, not the clock), with an AI tutor that **remembers your progress between
sessions** because the memory lives in files, not in the model.

There's no app to run. The "program" is a set of files the AI reads and writes. That's
deliberate: the structure comes first, and it works with any capable AI. This copy is
wired for **Claude** (`CLAUDE.md` + `.claude/skills/`).

This repo is a **language-agnostic template**. Out of the box the tracking files and plan
contain placeholders — the one-time **setup** step fills them in for your language.

## How it works

1. Open Claude (Claude Code) **in this folder**.
2. First time only: run **`/tutor-setup`** — it interviews you, writes your profile and a
   learning plan for your language, and creates your Obsidian review vault.
3. Each session run **`/session`**: it reads the **fixed plan**, your **profile**, and
   your **live progress**, runs a short lesson (review → new material → speaking →
   logging), and **writes your progress back** so next time it knows exactly where you
   are and what you keep missing.

## First run

Open Claude Code in this folder and run:

> `/tutor-setup`

Answer its questions (your language, goal, level, how you like to learn). It writes your
profile, a learning plan for your language, and your Obsidian review vault.

## Every session after that

> `/session`

That's it. Claude auto-reads `CLAUDE.md` on launch, and `/session` tells it to read your
tracking files and run today's lesson. (You can still just say "run today's session" in
plain words — the command is only a shortcut. Pass extra instructions after it, e.g.
`/session let's do a conversation day`.)

## What's in here

```
.
├── README.md              ← you are here
├── CLAUDE.md              ← the tutor's instructions (the brain); Claude auto-reads this
├── .claude/
│   ├── commands/
│   │   └── session.md     ← the /session shortcut to run today's lesson
│   └── skills/            ← the skills the tutor uses
│       ├── tutor-setup/       ← FIRST-RUN bootstrap (/tutor-setup): profile + plan + vault
│       ├── tutor-progress/    ← owns tracking write-back (Leitner boxes) + validator
│       ├── tutor-srs/         ← the spaced-repetition spec (Leitner + SM-2)
│       ├── tutor-obsidian/    ← owns the Obsidian vault write-back (grammar + vocab)
│       └── tutor-pronunciation/ ← click-to-hear audio in Obsidian
├── curriculum/
│   └── plan.md            ← the fixed A1→A2→B1 plan (template; filled by setup). Never edited after.
├── tracking/              ← your memory (filled as you learn)
│   ├── profile.json       ← who you are and why
│   ├── progress.json      ← current unit, box per item, weak spots, streak
│   └── log.md             ← plain-language journal of every session
├── reference/             ← (optional) your own source material
└── rehearse/              ← a tiny standalone flashcard app fed from your vault + progress
```

Your **review notes** live in a separate **Obsidian vault** (created during setup), so
they sync to your phone:

```
<your vault>/<Language>/
├── index.md               ← links to the grammar book + every unit's note
├── _template.md           ← shape of a unit note
├── unit-X.Y.md            ← per-unit VOCABULARY (words + verbs) + links to grammar
└── grammar/               ← the grammar book: one page per system + forms references
```

Grammar rules live **only** in the grammar book; unit notes hold vocabulary and link to
the relevant grammar pages. Vocabulary is introduced at an even pace (~8 new words a
session), tracked in `tracking/progress.json`.

**Plan vs tutor:** `curriculum/plan.md` is *what* you learn (fixed). `CLAUDE.md` is *how*
it's taught (swappable). You can rewrite the tutor's behavior without touching the plan.

## Design: the two roles, kept separate

- **The plan** (`curriculum/plan.md`) is stable. It's the map. It does not change.
- **The tracking** (`tracking/`) is alive. It records where you are on the map, adapts the
  daily exercises, and never lets a weak spot disappear.

This separation — a fixed structure to follow, plus an honest record of progress the
tutor acts on — is the whole idea.

## The rehearse app (optional)

`rehearse/rehearse.html` is a no-server flashcard drill that seeds from your Obsidian
forms references + `progress.json` boxes. Run `python3 rehearse/generate.py` to build it,
then open the HTML. **Note:** the generator's parser was written for Norwegian and needs
adapting to your language's forms layout (see the note at the top of `generate.py`). The
tutor's own warm-up already drives spaced repetition, so the app is a nice-to-have.

## Sharing / reusing this template

This is meant to be copied. To start fresh for a new learner or language, take the whole
repo, keep the framework (`CLAUDE.md`, `.claude/`, `curriculum/plan.md`, `rehearse/`), and
let `tutor-setup` refill `tracking/` and `plan.md`. Don't commit another person's
`tracking/` data.
