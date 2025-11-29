# TTS Voice Assets

This directory contains reference voice files for Coqui XTTS voice cloning.

## Voice Files

- `aico_default.wav` - Default AICO voice (optional)
  - If not present, XTTS will use its built-in voice
  - To add custom voice: Record 6-30 seconds of clear speech
  - Format: WAV, 22050 Hz, mono recommended

## Voice Cloning

XTTS can clone any voice from a short audio sample:

1. Record clear speech (6-30 seconds)
2. Save as WAV file in this directory
3. Update `TtsHandler` to use the new voice file

## Quality Guidelines

- Clear audio (no background noise)
- Natural speaking pace
- Consistent volume
- Emotional range (if desired)
