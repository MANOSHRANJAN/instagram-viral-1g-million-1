#!/bin/bash
# =============================================================================
# Transcribe audio files using whisper-cpp's whisper-cli (Homebrew, GPU-accelerated
# on Apple Silicon via Metal). Processes all audio in transcripts/ that don't
# already have a matching .txt.
# Usage: bash scripts/transcribe.sh <project-name>
# =============================================================================
PROJECT="$1"
if [ -z "$PROJECT" ]; then
  echo "Usage: bash scripts/transcribe.sh <project-name>"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRANSCRIPTS_DIR="$SCRIPT_DIR/../../research/$PROJECT/transcripts"
MODEL="$SCRIPT_DIR/../models/ggml-base.en.bin"

if [ ! -d "$TRANSCRIPTS_DIR" ]; then
  echo "No transcripts directory found for project: $PROJECT"
  exit 1
fi

if [ ! -f "$MODEL" ]; then
  echo "Whisper model not found at $MODEL"
  echo "Download it with:"
  echo "  curl -L -o \"$MODEL\" https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
  exit 1
fi

if ! command -v whisper-cli >/dev/null 2>&1; then
  echo "whisper-cli not found. Install with: brew install whisper-cpp"
  exit 1
fi

# whisper-cli needs 16kHz mono WAV input — convert from the downloaded m4a/mp3/etc.
AUDIO_FILES=$(find "$TRANSCRIPTS_DIR" -name "*.m4a" -o -name "*.mp3" -o -name "*.webm" -o -name "*.opus" | sort)
TOTAL=$(echo "$AUDIO_FILES" | grep -c "." || true)

if [ "$TOTAL" -eq 0 ]; then
  echo "No audio files to transcribe."
  exit 0
fi

echo ""
echo "========================================"
echo "  Transcribing $TOTAL audio files (whisper-cli, base.en)"
echo "  Project: $PROJECT"
echo "========================================"
echo ""

DONE=0
SKIPPED=0

for AUDIO in $AUDIO_FILES; do
  FILENAME=$(basename "$AUDIO")
  BASENAME="${FILENAME%.*}"
  TXT_FILE="$TRANSCRIPTS_DIR/$BASENAME.txt"
  WAV_FILE="$TRANSCRIPTS_DIR/$BASENAME.wav"

  if [ -f "$TXT_FILE" ]; then
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  DONE=$((DONE + 1))
  echo "  [$DONE/$TOTAL] $BASENAME..."

  # Convert to 16kHz mono WAV (whisper.cpp's required input format)
  ffmpeg -y -loglevel error -i "$AUDIO" -ar 16000 -ac 1 -c:a pcm_s16le "$WAV_FILE" 2>/dev/null

  if [ ! -f "$WAV_FILE" ]; then
    echo "    FAILED (audio conversion)"
    continue
  fi

  # whisper-cli writes <WAV_FILE>.txt next to the wav by default with -otxt
  whisper-cli -m "$MODEL" -f "$WAV_FILE" -otxt -of "$TRANSCRIPTS_DIR/$BASENAME" --no-prints >/dev/null 2>&1

  rm -f "$WAV_FILE"

  if [ -f "$TXT_FILE" ]; then
    echo "    ok ($(wc -w < "$TXT_FILE" | tr -d ' ') words)"
  else
    echo "    FAILED"
  fi
done

echo ""
echo "========================================"
echo "  Transcription complete!"
echo "  Transcribed: $DONE"
echo "  Skipped (already done): $SKIPPED"
echo "========================================"
