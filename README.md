# Frosty-Audio-Fixer

Frosty-Audio-Fixer is a small desktop utility for **batch probing and converting audio files** for Frosty / Frostbite modding workflows.

It is designed for the common “my audio isn’t in the right format” problem—quickly inspect a file’s properties (duration, sample rate, channels, codec) and convert it to a consistent output format.

## What it does

### Probe
- Reads audio metadata for selected files:
  - duration
  - sample rate
  - channel count
  - codec and bitrate (when available)

### Convert
- Batch converts audio into a consistent target format:
  - output: **WAV**
  - configurable sample rate, channels, and bit depth
  - optional overwrite protection

## Requirements

This tool uses **FFmpeg** (`ffmpeg` + `ffprobe`) for decoding and conversion.

- macOS: install with Homebrew  
  ```bash
  brew install ffmpeg
