---
name: demucs
description: Music source separation CLI for Demucs. Use when asked to separate music
  into stems, split stems, extract vocals from song, isolate drums, isolate bass,
  remove vocals, karaoke, acapella, instrumental track, stem separation, music demixing,
  source separation, split song into parts, extract instruments from music, vocal
  isolation, drum extraction, unmix audio, strip vocals, accompaniment extraction,
  background music removal, AI stem separation, separate instruments, isolate
  vocals, split tracks, demix, backing track, or any music stem splitting task.
---

# Demucs — cli-me skill

CLI-powered interface for Demucs (Meta's music source separation). This skill
wraps the real `demucs` executable — it does not reimplement neural network
inference in Python.

## Prerequisites

- Demucs must be installed: `pip install demucs`
  - For CUDA/GPU acceleration: install PyTorch with CUDA first from https://pytorch.org/get-started/locally/
  - torchcodec version must match PyTorch (see https://github.com/pytorch/torchcodec)
- ffmpeg **full-shared** build (required for audio loading and WAV/FLAC output):
  - Windows: install full-shared build from https://github.com/BtbN/FFmpeg-Builds/releases
    and ensure the shared DLLs are next to `ffmpeg.exe`
  - macOS: `brew install ffmpeg`
  - Linux: `apt install ffmpeg`
- Python 3.12+
- uv (Python package runner): https://docs.astral.sh/uv/getting-started/installation/

## CLI Commands

Run commands from the skill's `scripts/` directory:
```bash
cd <skill-dir>/scripts
uv run demucs_cli.py <command> [options]
```

Or from any directory using the full path:
```bash
uv run --project <skill-dir>/scripts <skill-dir>/scripts/demucs_cli.py <command> [options]
```

To discover available flags for any command:
```bash
uv run demucs_cli.py <command> --help
```

### Available Commands

| Command | Purpose |
|---------|---------|
| `separate` | Split audio into stems (vocals, drums, bass, other) |
| `list-models` | Show available pretrained models |

### Quick Examples

```bash
# Separate a song into 4 stems (vocals, drums, bass, other)
uv run demucs_cli.py separate song.mp3

# Extract vocals only (karaoke mode)
uv run demucs_cli.py separate song.mp3 --two-stems vocals

# Use the best quality model
uv run demucs_cli.py separate song.mp3 --model htdemucs_ft

# Force CPU processing
uv run demucs_cli.py separate song.mp3 --device cpu

# Output as MP3 instead of WAV
uv run demucs_cli.py separate song.mp3 --format mp3

# Reduce GPU memory usage
uv run demucs_cli.py separate song.mp3 --segment 7

# High quality with shift averaging
uv run demucs_cli.py separate song.mp3 --shifts 5

# List available models
uv run demucs_cli.py list-models
```

### Common Task Mapping

| Task | Command | Notes |
|------|---------|-------|
| Separate song into stems | `separate song.mp3` | 4 stems: vocals, drums, bass, other |
| Extract vocals (karaoke) | `separate song.mp3 --two-stems vocals` | Gets vocals + accompaniment |
| Remove vocals (instrumental) | `separate song.mp3 --two-stems vocals` | Use the `no_vocals.wav` output |
| Extract drums | `separate song.mp3 --two-stems drums` | Drums + everything else |
| Best quality separation | `separate song.mp3 --model htdemucs_ft --shifts 5` | 4-5x slower |
| Low VRAM GPU | `separate song.mp3 --segment 7` | Smaller chunks = less memory |
| Batch process folder | `separate *.mp3 --output ./stems` | All files in one call |
| MP3 output | `separate song.mp3 --format mp3 --mp3-bitrate 320` | Compressed output |

### Default Behavior

- **Device auto-detection:** CUDA GPU is used automatically if available, otherwise
  falls back to CPU. Override with `--device`.
- **Output directory:** Stems are saved to `./separated/{model}/{track}/` by default.
  Override with `--output`.
- **Processing time:** Separation is slow — expect 1-10 minutes per song depending
  on model, shifts, and hardware. The CLI enforces a 1-hour subprocess timeout.
  Use `timeout: 3600000` (or higher) in Bash tool calls, or `run_in_background: true`
  for long files or large batches.

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how something works under the hood, check
`references/source-analysis/`.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

**Important:** Always read an existing page before modifying it. Do not create
new pages that duplicate existing topics — update the existing page instead.

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Append a timestamped entry to `references/log.md` with what you did and
   what you learned
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
