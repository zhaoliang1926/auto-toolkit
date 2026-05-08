#!/bin/bash
# Voice chat - record mic, transcribe, get Claude response, speak back
# Requires: sox (brew install sox) or use macOS built-in recording
VOICE_DIR="$HOME/.claude/voice-chat"
mkdir -p "$VOICE_DIR"

record_audio() {
  local outfile="$VOICE_DIR/input_$(date +%s).wav"
  echo "Recording (press Ctrl+C to stop)..."
  # Use macOS built-in afrecord or sox
  if command -v rec &>/dev/null; then
    rec "$outfile" rate 16k silence 1 0.1 3% 1 3.0 3% 2>&1
  else
    # Fallback: use macOS swift/afplay recording via osascript
    osascript -e '
      set recordFile to "'"$outfile"'"
      do shell script "echo Recording 5 seconds..."
      do shell script "arecord -d 5 -f cd -t wav " & recordFile
    '
    # Simpler: use built-in audio recording
    arecord -d 8 -f S16_LE -r 16000 "$outfile" 2>/dev/null || \
    rec -r 16000 -c 1 "$outfile" trim 0 8 2>/dev/null || {
      echo "No recording tool available. Install sox: brew install sox"
      return 1
    }
  fi
  echo "$outfile"
}

main() {
  echo "Voice Chat - say something..."
  local audiofile=$(record_audio)
  if [ -z "$audiofile" ] || [ ! -f "$audiofile" ]; then
    echo "Recording failed. Install sox: brew install sox"
    exit 1
  fi

  # Transcribe via OpenAI Whisper API
  local token=$(python3 -c "
import json
with open('$HOME/.claude/settings.json') as f:
    d = json.load(f)
# Find DeepSeek or OpenAI key
print(d.get('apiKeys', {}).get('openai', ''))
" 2>/dev/null)

  if [ -z "$token" ]; then
    echo "No API token found for transcription"
    exit 1
  fi

  echo "Transcribing..."
  local text=$(curl -s https://api.openai.com/v1/audio/transcriptions \
    -H "Authorization: Bearer $token" \
    -F file="@$audiofile" \
    -F model="whisper-1" \
    -F language="zh" | python3 -c "import json,sys; print(json.load(sys.stdin).get('text',''))" 2>/dev/null)

  echo "You said: $text"

  # Speak response placeholder - actual Claude integration via stdin
  echo "Getting response..."
  echo "$text"
}

main "$@"
