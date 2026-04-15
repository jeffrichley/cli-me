---
name: ffmpeg
description: Media processing CLI for ffmpeg. Use when asked to convert video, compress
  video, extract audio, trim or clip video, resize video, add subtitles, remove
  background noise, normalize audio, create gif, stream video, HLS, DASH, RTMP,
  concatenate or merge videos, add watermark, create timelapse, slow motion, screen
  capture, ffprobe, podcast audio processing, or any media file manipulation.
---

# ffmpeg — cli-me skill

Intent-based CLI for ffmpeg and ffprobe. This skill wraps the real ffmpeg binary —
it does not process media in Python.

## Prerequisites

- ffmpeg and ffprobe must be installed and in PATH
  - Windows: `winget install ffmpeg` or download from https://ffmpeg.org/download.html
  - macOS: `brew install ffmpeg`
  - Linux: `apt install ffmpeg` or `dnf install ffmpeg`
- Python 3.12+

## CLI Commands

Run commands from the skill's `scripts/` directory:
```bash
cd <skill-dir>/scripts
uv run ffmpeg_cli.py <group> <command> [options]
```

Or from any directory using the full path:
```bash
uv run --project <skill-dir>/scripts <skill-dir>/scripts/ffmpeg_cli.py <group> <command> [options]
```

To discover available flags for any command:
```bash
uv run ffmpeg_cli.py <group> <command> --help
```

### Command Groups

| Group | Purpose |
|-------|---------|
| `convert` | Format conversion, compression, platform encoding, GIF, hardware accel |
| `extract` | Trim clips, extract audio, frames, sprite sheets |
| `transform` | Resize, crop, speed, watermark, subtitles, rotate, fade |
| `audio` | Normalize loudness, denoise, remove silence, music ducking |
| `combine` | Concatenate, mux audio+video, image sequences, compositing |
| `stream` | HLS, DASH, multi-bitrate, RTMP restream, fake live |
| `util` | Batch transcode, probe/validate, screen capture, surveillance |

### Quick Examples

```bash
# Convert MOV to MP4
uv run scripts/ffmpeg_cli.py convert format input.mov output.mp4

# Compress for web
uv run scripts/ffmpeg_cli.py convert compress input.mp4 output.mp4 --crf 23

# Extract audio as MP3
uv run scripts/ffmpeg_cli.py extract audio input.mp4 output.mp3

# Trim a clip
uv run scripts/ffmpeg_cli.py extract clip input.mp4 output.mp4 --start 00:01:30 --end 00:02:00

# Resize to 720p
uv run scripts/ffmpeg_cli.py transform resize input.mp4 output.mp4 --height 720

# Normalize podcast audio
uv run scripts/ffmpeg_cli.py audio normalize input.wav output.wav --target -16

# Create GIF
uv run scripts/ffmpeg_cli.py convert to-gif input.mp4 output.gif --fps 15 --width 480

# Probe file info
uv run scripts/ffmpeg_cli.py util probe input.mp4
```

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how a command works under the hood, check the
relevant technique page — it explains the ffmpeg flags, common mistakes,
and parameter recommendations.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Append a timestamped entry to `references/log.md` with what you did and
   what you learned
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
