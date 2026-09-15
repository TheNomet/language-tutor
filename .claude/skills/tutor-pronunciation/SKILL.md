---
name: tutor-pronunciation
description: Add or update click-to-hear pronunciation audio for target-language vocabulary in the learner's Obsidian vault. Use when they ask how a word/phrase is pronounced, to "hear" a word, to add audio to the forms references or unit notes, or mention pronunciation/TTS/audio. Plays INLINE in Obsidian (no browser switching).
---

# Pronunciation audio

Give the learner inline click-to-hear audio for target-language words/phrases **inside
Obsidian** — no switching to a browser. The mechanism: download a TTS mp3 into the vault
and embed it with Obsidian's audio-embed syntax `![[audio/<file>.mp3]]`, which renders an
inline play button on desktop and phone (mp3s iCloud-sync like the notes).

## Paths

- The OPEN Obsidian vault IS the language folder itself (it has its own `.obsidian/`),
  NOT the parent documents folder. Read the vault root from `tracking/profile.json`
  (`vault_path`). `![[audio/x.mp3]]` and the CSS snippet resolve relative to that root.
- Audio folder (create if missing): `<vault>/audio/`
- CSS snippet: `<vault>/.obsidian/snippets/tutor-audio.css` (use the language-folder
  vault, not the parent documents folder — wrong vault).
- Forms references that get audio columns: the `g*-noun-forms.md`, `g*-verb-forms.md`,
  `g*-adjective-forms.md` files the `tutor-obsidian` skill maintains.

## Fetching audio

TTS endpoint (returns an mp3 for any text in a given language; robotic but consistent,
good for rhythm and tricky sounds). Set `tl=<language-code>` for the target language
(e.g. `no` Norwegian, `de` German, `es` Spanish, `fr` French):

```
https://translate.google.com/translate_tts?ie=UTF-8&tl=<LANG>&client=tw-ob&q=<URL-ENCODED TEXT>
```

The setup skill records the right `tl` code in `tracking/profile.json` (`tts_lang`).
Download one file per word/phrase into the audio folder. Use a slugged filename (ascii,
no spaces): transliterate the language's diacritics consistently, spaces→`-`, lowercase.
Pronounce the form being learned (usually the definite/citation form for nouns, the
infinitive for verbs).

Helper script (in this skill dir): `scripts/fetch_audio.sh "<text>" "<slug>" "<lang>"`
— curls the mp3 into the vault audio folder and prints the embed line. Verify the result
is real audio, not an HTML error page:

```
file "<path>.mp3"   # must say: MPEG ADTS ... layer III
```

If the endpoint returns HTML/429 (rate-limited), wait and retry; keep requests modest
when batch-downloading a whole word list.

## Embedding in notes

Preferred method: a tiny local Obsidian plugin that renders inline code `` `snd:<slug>` ``
as a single ▶ play button playing `audio/<slug>.mp3` — a lone button, no timeline/kebab,
works desktop + iOS. Place one after each word form:

```
| English | citation | definite | plural | ... |
|---------|----------|----------|--------|-----|
| cup | en kopp `snd:en-kopp` | koppen `snd:koppen` | kopper `snd:kopper` | ... |
```

The slug must match the mp3 filename (same slugging rules). Button styling lives in the
`tutor-audio` CSS snippet.

Fallback if no plugin: the native embed `![[audio/x.mp3]]` still works but shows the
fuller player. (Vanilla CSS cannot reduce the native `<audio>` element to a lone button —
hence the small plugin is preferred if the learner wants the clean look.)

## Honest caveats to tell them

- It is a **robot voice** — fine for rhythm/sounds, not native-perfect. For truly natural
  pronunciation point them at Forvo (https://forvo.com/) or a weekly voice session with a
  voice assistant.
- Files accumulate in the vault; keep filenames slugged and deduped so re-runs don't
  create duplicates.
