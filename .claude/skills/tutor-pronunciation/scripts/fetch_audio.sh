#!/usr/bin/env bash
# Fetch a target-language TTS mp3 into the Obsidian vault audio folder.
# Usage: fetch_audio.sh "<text>" "<slug>" [<lang-code>] [<vault-path>]
#   e.g. fetch_audio.sh "hånden" "haanden" no
# lang-code defaults to $TTS_LANG or "no". vault-path defaults to $VAULT_PATH.
set -euo pipefail

TEXT="${1:?need text}"
SLUG="${2:?need output slug (ascii, no spaces)}"
LANG_CODE="${3:-${TTS_LANG:-no}}"
VAULT="${4:-${VAULT_PATH:?set VAULT_PATH env or pass vault path as arg 4}}"

AUDIO_DIR="$VAULT/audio"
mkdir -p "$AUDIO_DIR"
OUT="$AUDIO_DIR/$SLUG.mp3"

# URL-encode the text
ENC=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$TEXT")
URL="https://translate.google.com/translate_tts?ie=UTF-8&tl=$LANG_CODE&client=tw-ob&q=$ENC"

curl -sL -A "Mozilla/5.0" -o "$OUT" "$URL"

if file "$OUT" | grep -qi "MPEG ADTS"; then
  echo "OK: $OUT"
  echo "Embed: ![[audio/$SLUG.mp3]]"
else
  echo "FAILED (not audio — likely rate-limited/HTML): $OUT" >&2
  file "$OUT" >&2
  exit 1
fi
