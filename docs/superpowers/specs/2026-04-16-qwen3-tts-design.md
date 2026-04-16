# Qwen3-TTS Skill Design Spec

## Goal

Build a cli-me skill that wraps Qwen3-TTS (Alibaba's open-source TTS model) as an agent-native Typer CLI, covering text-to-speech generation, voice cloning, voice design, hardware inspection, and fine-tuning.

## Background

Qwen3-TTS is a family of multilingual TTS models (Apache 2.0) supporting 10 languages, 9 built-in speakers, voice cloning from 3 seconds of reference audio, voice design from natural language descriptions, and style control via instructions. It runs locally on GPU (CUDA) or CPU.

Unlike yt-dlp/ffmpeg skills that shell out to a binary, this skill imports the `qwen-tts` Python API directly because Qwen3-TTS is a Python ML model. This gives us control over GPU detection, model loading lifecycle, and richer feature access.

## Architecture

### In-Process Python API

The CLI imports `Qwen3TTSModel` from the `qwen-tts` package and calls it directly. No subprocess shelling. This means:

- **GPU auto-detection**: `torch.cuda.is_available()` at model load time, automatic fallback to CPU with a warning
- **Lazy model loading**: the model loads on the first command that needs it (not at CLI startup), so `info device` and `info speakers` are instant
- **Model stays loaded** within a single CLI invocation for batch operations

### Output Format

- Default output: WAV (native format from Qwen3-TTS)
- Optional `--format mp3|flac|ogg` post-processes via ffmpeg (if installed). If ffmpeg is not available and a non-WAV format is requested, error with install instructions.

### Default Model

- Default: `Qwen3-TTS-12Hz-1.7B-Base` (quality)
- Switchable via `--model 0.6b` for speed/lower VRAM

### Streaming

- Default: non-streaming (full generation, then write file)
- `--stream` flag: streaming generation (writes audio chunks as produced)

## Command Groups

### 1. `generate` — Core TTS

| Command | Description |
|---------|-------------|
| `generate text "Hello world" -o hello.wav` | Basic text-to-speech |
| `generate text "..." --speaker Aiden -o out.wav` | With built-in speaker |
| `generate text "..." --speaker Aiden --instruct "Speak with excitement" -o out.wav` | With style control |
| `generate text "..." --lang en -o out.wav` | Explicit language selection |

**Parameters:**
- `text` (positional, required): text to synthesize
- `--output / -o` (required): output file path
- `--speaker` (optional, default: model default): built-in speaker name
- `--instruct` (optional): style/emotion instruction in natural language
- `--lang` (optional): language code (en, zh, ja, ko, de, fr, ru, pt, es, it)
- `--model` (optional, default: "1.7b"): model size ("1.7b" or "0.6b")
- `--format` (optional, default: "wav"): output format (wav, mp3, flac, ogg)
- `--stream` (optional, default: false): enable streaming generation
- `--device` (optional): force device (cuda, cpu, mps). Auto-detected if omitted.

### 2. `clone` — Voice Cloning

| Command | Description |
|---------|-------------|
| `clone text "..." --reference voice.wav --ref-text "transcript" -o out.wav` | Clone from reference audio |

**Parameters:**
- `text` (positional, required): text to synthesize
- `--reference` (required): path to reference audio file (3+ seconds)
- `--ref-text` (required): transcript of the reference audio
- `--output / -o` (required): output file path
- `--instruct` (optional): style instruction
- `--lang` (optional): language code
- `--model` (optional): model size
- `--format` (optional): output format
- `--device` (optional): force device

### 3. `design` — Voice from Description

| Command | Description |
|---------|-------------|
| `design text "..." --description "warm, deep male voice" -o out.wav` | Design voice from description |

**Parameters:**
- `text` (positional, required): text to synthesize
- `--description` (required): natural language voice description
- `--output / -o` (required): output file path
- `--instruct` (optional): additional style instruction
- `--lang` (optional): language code
- `--model` (optional): model size
- `--format` (optional): output format
- `--device` (optional): force device

### 4. `info` — Inspection

| Command | Description |
|---------|-------------|
| `info speakers` | List available built-in speakers (JSON by default, `--pretty` for readable) |
| `info languages` | List supported languages (JSON by default, `--pretty` for readable) |
| `info device` | Show GPU/CPU status, VRAM, model loaded status |

**Parameters for speakers/languages:**
- `--pretty` (optional): human-readable output instead of JSON
- `--model` (optional): model size (speakers may differ between models)

**Parameters for device:**
- No parameters. Always prints device info.

### 5. `finetune` — Custom Voice Training

| Command | Description |
|---------|-------------|
| `finetune prepare --audio-dir ./samples/ --output-dir ./dataset/` | Prepare training data from audio files |
| `finetune train --dataset ./dataset/ --output-dir ./model/` | Train custom voice model |
| `finetune generate "..." --model-dir ./model/ -o out.wav` | Generate with fine-tuned model |

**Parameters for prepare:**
- `--audio-dir` (required): directory of WAV files
- `--output-dir` (required): where to write prepared dataset
- `--lang` (optional, default: "en"): language of the audio

**Parameters for train:**
- `--dataset` (required): path to prepared dataset
- `--output-dir` (required): where to save the trained model
- `--base-model` (optional, default: "1.7b"): base model to fine-tune from
- `--epochs` (optional): number of training epochs
- `--batch-size` (optional): training batch size
- `--device` (optional): force device

**Parameters for generate:**
- `text` (positional, required): text to synthesize
- `--model-dir` (required): path to fine-tuned model directory
- `--output / -o` (required): output file path
- `--instruct` (optional): style instruction
- `--lang` (optional): language code
- `--format` (optional): output format
- `--device` (optional): force device

## File Structure

```
skill-repo/qwen3-tts/
├── SKILL.md
├── scripts/
│   ├── pyproject.toml
│   ├── qwen3_tts_cli.py              # entry point shim
│   └── qwen3_tts_cli/
│       ├── __init__.py                # exports app
│       ├── __main__.py                # python -m support
│       ├── backend.py                 # model loading, GPU detection, audio I/O
│       ├── generate.py                # generate command group (thin wrapper)
│       ├── clone.py                   # clone command group
│       ├── design.py                  # design command group
│       ├── info.py                    # info command group
│       ├── finetune.py                # finetune command group
│       └── commands/
│           ├── __init__.py
│           ├── generate_text.py       # TTS generation logic
│           ├── clone_text.py          # voice cloning logic
│           ├── design_text.py         # voice design logic
│           ├── info_speakers.py       # list speakers
│           ├── info_languages.py      # list languages
│           ├── info_device.py         # device detection
│           ├── finetune_prepare.py    # dataset preparation
│           ├── finetune_train.py      # training logic
│           └── finetune_generate.py   # generation from fine-tuned model
└── references/
    ├── index.md
    ├── log.md
    ├── gotchas.md
    ├── source-analysis/
    │   ├── analyzed-version.md
    │   ├── api-surface.md
    │   ├── cli-interface.md
    │   ├── internal-architecture.md
    │   └── key-functions.md
    └── techniques/
        ├── basic-tts.md
        ├── voice-cloning.md
        ├── voice-design.md
        ├── speaker-styles.md
        ├── multilingual.md
        ├── fine-tuning.md
        └── gpu-optimization.md
```

## Dependencies

```toml
[project]
name = "qwen3-tts-cli"
version = "0.1.0"
description = "Agent-native CLI for Qwen3-TTS"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15.0",
    "rich>=13.0.0",
    "qwen-tts>=0.1.0",
    "torch>=2.0.0",
    "soundfile>=0.12.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Backend Module Design

```python
# backend.py — key functions

def detect_device(force: str | None = None) -> str:
    """Auto-detect best device. Returns 'cuda', 'mps', or 'cpu'."""
    if force:
        return force
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    typer.echo("WARNING: No GPU detected. Using CPU (will be slow).", err=True)
    return "cpu"

def load_model(model_size: str = "1.7b", device: str | None = None) -> Qwen3TTSModel:
    """Load model with auto device detection. Caches after first load."""
    ...

def save_audio(audio_data, path: str, format: str = "wav", sample_rate: int = 24000):
    """Save audio, converting format via ffmpeg if needed."""
    ...
```

## Error Handling

- **No GPU**: warn and fall back to CPU (never fail silently)
- **Model not downloaded**: auto-download from HuggingFace on first use (qwen-tts handles this)
- **Invalid speaker name**: list valid speakers in error message
- **Invalid language**: list valid languages in error message
- **ffmpeg not installed** (for non-WAV output): error with install instructions
- **Reference audio too short** (cloning): error with minimum duration note
- **VRAM out of memory**: suggest using 0.6b model or CPU fallback

## Testing Strategy

- **Tier 1 (command graph)**: test that each command builds the correct function call args (mock the model)
- **Tier 2 (integration)**: test actual generation with the 0.6B model (faster, lower VRAM) against real audio output — verify WAV file is valid, has correct sample rate, non-zero duration
- **Tier 3 (manual)**: generate samples for human listening review

## Open Questions (Resolved)

- Default model: **1.7B** (user chose quality over speed)
- Installation: **local** via pip
- GPU detection: **automatic** with CPU fallback
