---
name: pyannote
description: Speaker diarization and audio analysis CLI for pyannote.audio — diarize speakers, detect speech activity, verify speakers, extract embeddings. Use when asked to "diarize", "who spoke when", "speaker detection", "voice activity", "speaker verification", "speaker embedding", or "identify speakers" in audio files.
---

# pyannote.audio — cli-me skill

CLI-powered interface for pyannote.audio. This skill wraps the real pyannote.audio
Python API — it uses Pipeline.from_pretrained() and Inference to run speaker
diarization, voice activity detection, speaker verification, and embedding extraction.

## Prerequisites

- pyannote.audio must be installed: `pip install pyannote.audio`
- ffmpeg must be installed (used internally for audio decoding of MP3, M4A, etc.)
- A HuggingFace token with model access: set `HF_TOKEN` env var or run `huggingface-cli login`
- Accept model terms at https://huggingface.co/pyannote/speaker-diarization-community-1
- Python 3.12+

## CLI Commands

Run commands via:
```bash
uv run scripts/pyannote_cli.py <command> [options]
```

### Available Commands

**diarize** — Speaker diarization ("who spoke when")
- `diarize FILE` — diarize an audio file, output RTTM
- Options: `--output`, `--format {rttm,json,txt}`, `--num-speakers`, `--min-speakers`, `--max-speakers`, `--device`, `--token`

**vad** — Voice activity detection (speech regions)
- `vad FILE` — detect speech regions in audio (runs diarization internally)
- Options: `--output`, `--format {rttm,json,txt}`, `--device`, `--token`

**verify** — Speaker verification (same speaker?)
- `verify FILE_A FILE_B` — compare two audio samples
- Options: `--threshold`, `--model {resnet34,embedding}`, `--device`, `--token`

**embed** — Extract speaker embeddings
- `embed FILE` — extract embedding vector from audio
- Options: `--output`, `--model {resnet34,embedding}`, `--device`, `--token`

**info** — Show audio file information
- `info FILE` — show duration, sample rate, channels

## Default Behavior

- **Output location:** stdout by default, `--output FILE` to save
- **Output format:** RTTM for diarize/vad, JSON for embed, text for verify
- **Device:** auto-detected (CUDA > MPS > CPU)
- **Token:** reads from `HF_TOKEN` environment variable by default
- **First run:** downloads ~500MB of model weights (cached for subsequent runs)
- **Processing time:** ~6 min per hour of audio on CPU, ~1 min on GPU
- **Timeout guidance:** Use `timeout: 600000` for Bash tool calls on files > 10 min.
  For files > 30 min, run in background.

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how something works under the hood, check
`references/source-analysis/`.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Log what you did: `clime log append --skill pyannote --message "<what you did and learned>" --log-file references/log.md`
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
