# Qwen3-TTS Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cli-me skill that wraps Qwen3-TTS as an agent-native Typer CLI with text-to-speech, voice cloning, voice design, info, and fine-tuning commands.

**Architecture:** Unlike yt-dlp/ffmpeg skills that shell out to binaries, this skill imports the `qwen-tts` Python API directly (in-process). GPU detection is automatic via `torch.cuda.is_available()`. The model loads lazily on first command that needs it. Output is WAV by default with optional ffmpeg conversion.

**Tech Stack:** Python 3.12+, typer, rich, qwen-tts, torch, soundfile

**Spec:** `docs/superpowers/specs/2026-04-16-qwen3-tts-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `skill-repo/qwen3-tts/SKILL.md` | Create | Skill definition with frontmatter, commands, examples |
| `skill-repo/qwen3-tts/scripts/pyproject.toml` | Create | Dependencies and entry point |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli.py` | Create | Entry point shim for `uv run` |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/__init__.py` | Create | Exports `app`, registers command groups |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/__main__.py` | Create | `python -m` support |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/backend.py` | Create | Model loading, GPU detection, audio I/O |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/generate.py` | Create | Generate command group (thin wrapper) |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/clone.py` | Create | Clone command group (thin wrapper) |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/design.py` | Create | Design command group (thin wrapper) |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/info.py` | Create | Info command group (thin wrapper) |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/finetune.py` | Create | Finetune command group (thin wrapper) |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/__init__.py` | Create | Logic layer docstring |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/generate_text.py` | Create | TTS generation logic |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/clone_text.py` | Create | Voice cloning logic |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/design_text.py` | Create | Voice design logic |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/info_speakers.py` | Create | List speakers |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/info_languages.py` | Create | List languages |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/info_device.py` | Create | Device detection info |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/finetune_prepare.py` | Create | Dataset preparation |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/finetune_train.py` | Create | Model training |
| `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/finetune_generate.py` | Create | Generation from fine-tuned model |
| `skill-repo/qwen3-tts/references/` | Create | Wiki directory structure |
| `qa/qwen3-tts/` | Create | Test directory |

All paths relative to `E:/workspaces/tools/cli-me/`.

---

## Phase 1: Research

### Task 1: Clone source and install Qwen3-TTS

**Files:**
- Create: `tmp/source-analysis/qwen3-tts/` (cloned repo)

- [ ] **Step 1: Clone the Qwen3-TTS repository**

```bash
git clone --depth 1 https://github.com/QwenLM/Qwen3-TTS.git tmp/source-analysis/qwen3-tts
```

- [ ] **Step 2: Install qwen-tts into the skill's venv**

```bash
cd skill-repo/qwen3-tts/scripts
mkdir -p skill-repo/qwen3-tts/scripts
```

First create a minimal pyproject.toml so uv can create the venv:

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

```bash
cd skill-repo/qwen3-tts/scripts && uv sync
```

- [ ] **Step 3: Verify installation and GPU detection**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB')
from qwen_tts import Qwen3TTSModel
print(f'qwen-tts imported successfully')
print(f'Qwen3TTSModel: {Qwen3TTSModel}')
"
```

Expected: CUDA detected (if GPU present), qwen-tts imports successfully.

- [ ] **Step 4: Verify the installed qwen-tts API surface**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -c "
from qwen_tts import Qwen3TTSModel
# List all public methods
methods = [m for m in dir(Qwen3TTSModel) if not m.startswith('_')]
for m in methods:
    print(m)
"
```

Record the output — this is the real API surface we'll wrap. Compare against the README to catch any version discrepancies.

- [ ] **Step 5: Commit**

```bash
git add skill-repo/qwen3-tts/scripts/pyproject.toml
git commit -m "feat(qwen3-tts): initialize skill with pyproject.toml and dependencies"
```

---

### Task 2: Analyze source and write wiki

**Files:**
- Create: `skill-repo/qwen3-tts/references/source-analysis/analyzed-version.md`
- Create: `skill-repo/qwen3-tts/references/source-analysis/api-surface.md`
- Create: `skill-repo/qwen3-tts/references/source-analysis/cli-interface.md`
- Create: `skill-repo/qwen3-tts/references/source-analysis/internal-architecture.md`
- Create: `skill-repo/qwen3-tts/references/source-analysis/key-functions.md`

- [ ] **Step 1: Read the cloned source to document the API**

Read these files from `tmp/source-analysis/qwen3-tts/`:
- `README.md` — full API examples
- `src/qwen_tts/model.py` (or similar) — the `Qwen3TTSModel` class
- `docs/API.md` — parameter details
- `finetuning/sft_12hz.py` — fine-tuning script
- `finetuning/README.md` — fine-tuning docs
- `examples/test_model_12hz_base.py` — usage examples

For each file, extract: function signatures, parameter types, return types, default values.

- [ ] **Step 2: Write source analysis pages**

Write the 5 source analysis pages based on what you found. Each must include:
- File paths and line numbers from the cloned source
- Exact function signatures (copy from source, don't paraphrase)
- Version information (git tag/commit from the clone)

`analyzed-version.md` should record:
- Git commit hash from `tmp/source-analysis/qwen3-tts/`
- Installed qwen-tts version from pip
- Date analyzed

`api-surface.md` should document every method on `Qwen3TTSModel`:
- `from_pretrained(model_name, device_map, dtype, attn_implementation)` → `Qwen3TTSModel`
- `generate_custom_voice(text, language, speaker, instruct=None)` → `(wavs, sr)`
- `generate_voice_clone(text, language, ref_audio, ref_text, ...)` → `(wavs, sr)`
- `generate_voice_design(text, language, instruct)` → `(wavs, sr)`
- `create_voice_clone_prompt(ref_audio, ref_text, ...)` → prompt items
- `get_supported_speakers()` → `list[str]`
- `get_supported_languages()` → `list[str]`

`cli-interface.md` should note: Qwen3-TTS has no native CLI — the `qwen-tts-cli` package on PyPI is a third-party wrapper. Our skill wraps the Python API directly.

`key-functions.md` should document the generation kwargs:
- `max_new_tokens`, `top_p`, `top_k`, `temperature`, `repetition_penalty`
- `subtalker_dosample`, `subtalker_top_k`, `subtalker_top_p`, `subtalker_temperature`

- [ ] **Step 3: Commit**

```bash
git add skill-repo/qwen3-tts/references/source-analysis/
git commit -m "docs(qwen3-tts): add source analysis from cloned repo"
```

---

### Task 3: Write technique wiki pages

**Files:**
- Create: `skill-repo/qwen3-tts/references/techniques/basic-tts.md`
- Create: `skill-repo/qwen3-tts/references/techniques/voice-cloning.md`
- Create: `skill-repo/qwen3-tts/references/techniques/voice-design.md`
- Create: `skill-repo/qwen3-tts/references/techniques/speaker-styles.md`
- Create: `skill-repo/qwen3-tts/references/techniques/multilingual.md`
- Create: `skill-repo/qwen3-tts/references/techniques/fine-tuning.md`
- Create: `skill-repo/qwen3-tts/references/techniques/gpu-optimization.md`
- Create: `skill-repo/qwen3-tts/references/index.md`
- Create: `skill-repo/qwen3-tts/references/log.md`
- Create: `skill-repo/qwen3-tts/references/gotchas.md`

- [ ] **Step 1: Research the web for best practices and tutorials**

Search for:
- Qwen3-TTS best practices and optimization
- Voice cloning techniques and quality tips
- Fine-tuning guides and dataset preparation
- Known issues and workarounds
- GPU memory optimization

- [ ] **Step 2: Write technique pages**

Each page follows the standard format: title, tags, When to Use, Technique, CLI Commands (using our planned CLI syntax), Under the Hood, Gotchas, Sources, Learned from Usage.

Key pages:
- `basic-tts.md` — text to speech with built-in speakers, language selection, output formats
- `voice-cloning.md` — reference audio requirements (3+ seconds, clean audio), transcript accuracy, clone prompt reuse
- `voice-design.md` — writing effective voice descriptions, supported attributes
- `speaker-styles.md` — the 9 built-in speakers, which languages they support, instruct examples
- `multilingual.md` — 10 languages, auto-detection vs explicit, mixed-language handling
- `fine-tuning.md` — dataset preparation, training parameters, hardware requirements, output model format
- `gpu-optimization.md` — VRAM requirements per model, bfloat16 vs float16, flash attention, CPU fallback

- [ ] **Step 3: Write operational wiki files**

`index.md` — table of contents linking all source-analysis and technique pages.
`log.md` — first entry: "2026-04-16: Initial research completed. Analyzed Qwen3-TTS. Created source analysis and technique pages."
`gotchas.md` — document issues found during research (e.g., model download on first use, VRAM requirements, flash attention optional).

- [ ] **Step 4: Commit**

```bash
git add skill-repo/qwen3-tts/references/
git commit -m "docs(qwen3-tts): add technique wiki and operational files"
```

---

## Phase 2: Scaffold

### Task 4: Create CLI scaffold and SKILL.md

**Files:**
- Create: `skill-repo/qwen3-tts/SKILL.md`
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli.py`
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/__init__.py`
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/__main__.py`
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/__init__.py`

- [ ] **Step 1: Create the package structure**

`skill-repo/qwen3-tts/scripts/qwen3_tts_cli/__init__.py`:
```python
"""Agent-native CLI for Qwen3-TTS."""

import typer

app = typer.Typer(
    name="qwen3-tts-cli",
    help="Agent-native CLI for Qwen3-TTS — text-to-speech, voice cloning, voice design, and fine-tuning.",
    no_args_is_help=True,
)


def register_commands() -> None:
    """Register all command groups."""
    from . import generate, clone, design, info, finetune  # noqa: F401


register_commands()
```

`skill-repo/qwen3-tts/scripts/qwen3_tts_cli/__main__.py`:
```python
"""Allow `python -m qwen3_tts_cli`."""

from . import app

app()
```

`skill-repo/qwen3-tts/scripts/qwen3_tts_cli.py`:
```python
"""Entry point for uv run qwen3_tts_cli.py"""
from qwen3_tts_cli import app

if __name__ == "__main__":
    app()
```

`skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/__init__.py`:
```python
"""Logic layer — independently testable command functions."""
```

- [ ] **Step 2: Create stub command group files**

Create empty stubs so the CLI loads. Each file follows this pattern:

`skill-repo/qwen3-tts/scripts/qwen3_tts_cli/generate.py`:
```python
"""Generate command group — text-to-speech with built-in speakers."""

import typer

from . import app

generate_app = typer.Typer(help="Text-to-speech generation with built-in speakers.", no_args_is_help=True)
app.add_typer(generate_app, name="generate")
```

Create the same pattern for `clone.py`, `design.py`, `info.py`, `finetune.py` with appropriate help text:
- `clone.py`: "Voice cloning from reference audio."
- `design.py`: "Voice design from natural language descriptions."
- `info.py`: "Inspect speakers, languages, and device info."
- `finetune.py`: "Fine-tune custom voice models."

- [ ] **Step 3: Verify scaffold loads**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m qwen3_tts_cli --help
```

Expected: shows all 5 command groups.

- [ ] **Step 4: Write SKILL.md**

Use the skill template from `.claude/skills/cli-me-meta/references/skill-template.md`. Key content:

Frontmatter:
```yaml
---
name: qwen3-tts
description: Text-to-speech generation, voice cloning, and voice design using Qwen3-TTS.
  Wraps the qwen-tts Python API for headless agent use. Use when asked to "generate
  speech", "text to speech", "TTS", "clone voice", "voice cloning", "design a voice",
  "create voiceover", "narrate", "read aloud", "synthesize speech", or "fine-tune TTS".
---
```

Body: prerequisites, CLI commands for all 5 groups with examples, default behavior (1.7B model, auto GPU, WAV output, force-overwrites equivalent), knowledge base reference, and write-back instructions (copy verbatim from `references/write-back-instructions.md`).

Include the ffmpeg/yt-dlp disambiguation pattern:
> **Note:** qwen3-tts generates speech from text. For extracting/processing existing audio, use the ffmpeg or demucs skills.

- [ ] **Step 5: Add registry entry**

```bash
clime registry add \
  --name "qwen3-tts" \
  --description "Text-to-speech, voice cloning, and voice design using Qwen3-TTS" \
  --category "audio" \
  --tags "tts,speech,voice,cloning,synthesis,ai" \
  --version "0.1.0" \
  --software-url "https://github.com/QwenLM/Qwen3-TTS" \
  --source-repo "https://github.com/QwenLM/Qwen3-TTS.git"
```

- [ ] **Step 6: Commit**

```bash
git add skill-repo/qwen3-tts/SKILL.md skill-repo/qwen3-tts/scripts/
git commit -m "feat(qwen3-tts): create CLI scaffold with 5 command groups"
```

---

### Task 5: Create backend module

**Files:**
- Create: `skill-repo/qwen3-tts/tests/__init__.py`
- Create: `skill-repo/qwen3-tts/tests/test_backend.py`
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/backend.py`

- [ ] **Step 1: Write failing tests for backend**

```python
"""Tests for the backend module — device detection and audio I/O."""

import pytest
from unittest.mock import patch, MagicMock


def test_detect_device_cuda_available():
    with patch("torch.cuda.is_available", return_value=True):
        from qwen3_tts_cli.backend import detect_device
        assert detect_device() == "cuda"


def test_detect_device_mps_fallback():
    with patch("torch.cuda.is_available", return_value=False), \
         patch("torch.backends.mps.is_available", return_value=True):
        from qwen3_tts_cli.backend import detect_device
        assert detect_device() == "mps"


def test_detect_device_cpu_fallback():
    with patch("torch.cuda.is_available", return_value=False), \
         patch("torch.backends.mps.is_available", return_value=False):
        from qwen3_tts_cli.backend import detect_device
        assert detect_device() == "cpu"


def test_detect_device_force_overrides():
    from qwen3_tts_cli.backend import detect_device
    assert detect_device(force="cpu") == "cpu"


def test_model_name_from_size():
    from qwen3_tts_cli.backend import model_name_from_size
    assert model_name_from_size("1.7b") == "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    assert model_name_from_size("0.6b") == "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"


def test_model_name_invalid_size():
    from qwen3_tts_cli.backend import model_name_from_size
    with pytest.raises(ValueError, match="Unknown model size"):
        model_name_from_size("3b")


def test_base_model_name_from_size():
    from qwen3_tts_cli.backend import base_model_name_from_size
    assert base_model_name_from_size("1.7b") == "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    assert base_model_name_from_size("0.6b") == "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m pytest ../tests/test_backend.py -v
```

Expected: FAIL — backend module doesn't exist.

- [ ] **Step 3: Implement backend module**

```python
"""Backend utilities for Qwen3-TTS CLI — model loading, device detection, audio I/O."""

import subprocess
import shutil
from pathlib import Path

import torch
import typer

# Model name mappings
CUSTOM_VOICE_MODELS = {
    "1.7b": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "0.6b": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
}

BASE_MODELS = {
    "1.7b": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "0.6b": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
}

# Cached model instance
_model_cache: dict = {}


def detect_device(force: str | None = None) -> str:
    """Auto-detect best available device. Returns 'cuda', 'mps', or 'cpu'."""
    if force:
        return force
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    typer.echo("WARNING: No GPU detected. Using CPU (will be slow).", err=True)
    return "cpu"


def model_name_from_size(size: str) -> str:
    """Return the HuggingFace model name for a CustomVoice model size."""
    if size not in CUSTOM_VOICE_MODELS:
        valid = ", ".join(sorted(CUSTOM_VOICE_MODELS))
        raise ValueError(f"Unknown model size '{size}'. Valid sizes: {valid}")
    return CUSTOM_VOICE_MODELS[size]


def base_model_name_from_size(size: str) -> str:
    """Return the HuggingFace model name for a Base model size (for fine-tuning/cloning)."""
    if size not in BASE_MODELS:
        valid = ", ".join(sorted(BASE_MODELS))
        raise ValueError(f"Unknown model size '{size}'. Valid sizes: {valid}")
    return BASE_MODELS[size]


def load_model(model_size: str = "1.7b", device: str | None = None):
    """Load a Qwen3-TTS CustomVoice model with caching.

    Returns the loaded model instance. Caches by (model_size, device) so
    subsequent calls with the same args return the same instance.
    """
    device = detect_device(device)
    cache_key = (model_size, device)
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    from qwen_tts import Qwen3TTSModel

    model_name = model_name_from_size(model_size)
    dtype = torch.bfloat16 if device != "cpu" else torch.float32

    model = Qwen3TTSModel.from_pretrained(
        model_name,
        device_map=f"{device}:0" if device == "cuda" else device,
        dtype=dtype,
    )
    _model_cache[cache_key] = model
    return model


def save_audio(
    audio_data,
    sample_rate: int,
    path: str,
    format: str = "wav",
) -> Path:
    """Save audio data to a file. Converts format via ffmpeg if not WAV."""
    import soundfile as sf

    output_path = Path(path)

    if format == "wav":
        sf.write(str(output_path), audio_data, sample_rate)
    else:
        # Write WAV to temp, convert via ffmpeg
        tmp_wav = output_path.with_suffix(".tmp.wav")
        sf.write(str(tmp_wav), audio_data, sample_rate)

        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            tmp_wav.unlink()
            typer.echo(
                f"ERROR: ffmpeg not found. Install ffmpeg to convert to {format}.\n"
                f"Or use --format wav (the default).",
                err=True,
            )
            raise typer.Exit(code=1)

        subprocess.run(
            [ffmpeg, "-y", "-i", str(tmp_wav), str(output_path)],
            check=True,
            capture_output=True,
        )
        tmp_wav.unlink()

    return output_path
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m pytest ../tests/test_backend.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skill-repo/qwen3-tts/scripts/qwen3_tts_cli/backend.py skill-repo/qwen3-tts/tests/
git commit -m "feat(qwen3-tts): add backend module with device detection and model loading"
```

---

## Phase 3: QA-First Implementation

### Task 6: Implement `info` command group

This group doesn't need model loading for `device`, and uses light model calls for `speakers`/`languages`. Good starting point to verify the full pipeline works.

**Files:**
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/info_device.py`
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/info_speakers.py`
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/info_languages.py`
- Create: `skill-repo/qwen3-tts/tests/test_info.py`
- Modify: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/info.py`
- Create: `qa/qwen3-tts/__init__.py`
- Create: `qa/qwen3-tts/test_info_commands.py`

- [ ] **Step 1: Write failing unit tests**

`skill-repo/qwen3-tts/tests/test_info.py`:
```python
"""Tests for info command logic."""

import json
from unittest.mock import patch, MagicMock

from qwen3_tts_cli.commands.info_device import get_device_info
from qwen3_tts_cli.commands.info_speakers import get_speakers, format_speakers
from qwen3_tts_cli.commands.info_languages import get_languages, format_languages


def test_get_device_info_cuda():
    with patch("torch.cuda.is_available", return_value=True), \
         patch("torch.cuda.get_device_name", return_value="NVIDIA RTX 4090"), \
         patch("torch.cuda.get_device_properties") as mock_props:
        mock_props.return_value = MagicMock(total_mem=24 * 1024**3)
        info = get_device_info()
        assert info["device"] == "cuda"
        assert info["gpu_name"] == "NVIDIA RTX 4090"
        assert info["vram_gb"] > 0


def test_get_device_info_cpu():
    with patch("torch.cuda.is_available", return_value=False), \
         patch("torch.backends.mps.is_available", return_value=False):
        info = get_device_info()
        assert info["device"] == "cpu"
        assert info["gpu_name"] is None


def test_format_speakers_pretty():
    speakers = ["Aiden", "Bella", "Carlos"]
    output = format_speakers(speakers, pretty=True)
    assert "Aiden" in output
    assert "Bella" in output


def test_format_speakers_json():
    speakers = ["Aiden", "Bella"]
    output = format_speakers(speakers, pretty=False)
    parsed = json.loads(output)
    assert parsed == ["Aiden", "Bella"]


def test_format_languages_pretty():
    languages = ["English", "Chinese"]
    output = format_languages(languages, pretty=True)
    assert "English" in output


def test_format_languages_json():
    languages = ["English", "Chinese"]
    output = format_languages(languages, pretty=False)
    parsed = json.loads(output)
    assert parsed == ["English", "Chinese"]
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m pytest ../tests/test_info.py -v
```

- [ ] **Step 3: Implement info command logic modules**

`commands/info_device.py`:
```python
"""Logic for info device command."""

import torch


def get_device_info() -> dict:
    """Return device information as a dict."""
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        return {
            "device": "cuda",
            "gpu_name": torch.cuda.get_device_name(0),
            "vram_gb": round(props.total_mem / 1024**3, 1),
        }
    if torch.backends.mps.is_available():
        return {
            "device": "mps",
            "gpu_name": "Apple Silicon",
            "vram_gb": None,
        }
    return {
        "device": "cpu",
        "gpu_name": None,
        "vram_gb": None,
    }


def format_device_info(info: dict, pretty: bool = False) -> str:
    """Format device info as JSON or human-readable."""
    if pretty:
        lines = [f"Device: {info['device']}"]
        if info["gpu_name"]:
            lines.append(f"GPU: {info['gpu_name']}")
        if info["vram_gb"]:
            lines.append(f"VRAM: {info['vram_gb']} GB")
        return "\n".join(lines)
    import json
    return json.dumps(info, indent=2)
```

`commands/info_speakers.py`:
```python
"""Logic for info speakers command."""

import json


def get_speakers(model) -> list[str]:
    """Get supported speakers from a loaded model."""
    return model.get_supported_speakers()


def format_speakers(speakers: list[str], pretty: bool = False) -> str:
    """Format speaker list as JSON or human-readable."""
    if pretty:
        lines = [f"Available speakers ({len(speakers)}):"]
        for i, s in enumerate(speakers, 1):
            lines.append(f"  {i}. {s}")
        return "\n".join(lines)
    return json.dumps(speakers, indent=2)
```

`commands/info_languages.py`:
```python
"""Logic for info languages command."""

import json


def get_languages(model) -> list[str]:
    """Get supported languages from a loaded model."""
    return model.get_supported_languages()


def format_languages(languages: list[str], pretty: bool = False) -> str:
    """Format language list as JSON or human-readable."""
    if pretty:
        lines = [f"Supported languages ({len(languages)}):"]
        for i, lang in enumerate(languages, 1):
            lines.append(f"  {i}. {lang}")
        return "\n".join(lines)
    return json.dumps(languages, indent=2)
```

- [ ] **Step 4: Wire up info.py thin wrapper**

```python
"""Info command group — inspect speakers, languages, and device info."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import load_model
from .commands import info_device, info_speakers, info_languages

info_app = typer.Typer(help="Inspect speakers, languages, and device info.", no_args_is_help=True)
app.add_typer(info_app, name="info")


@info_app.command()
def device() -> None:
    """Show GPU/CPU status and available hardware."""
    info = info_device.get_device_info()
    typer.echo(info_device.format_device_info(info, pretty=True))


@info_app.command()
def speakers(
    model_size: Annotated[str, typer.Option("--model", help="Model size (1.7b or 0.6b)")] = "1.7b",
    pretty: Annotated[bool, typer.Option("--pretty", help="Human-readable output")] = False,
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """List available built-in speakers."""
    model = load_model(model_size, device)
    speaker_list = info_speakers.get_speakers(model)
    typer.echo(info_speakers.format_speakers(speaker_list, pretty=pretty))


@info_app.command()
def languages(
    model_size: Annotated[str, typer.Option("--model", help="Model size (1.7b or 0.6b)")] = "1.7b",
    pretty: Annotated[bool, typer.Option("--pretty", help="Human-readable output")] = False,
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """List supported languages."""
    model = load_model(model_size, device)
    lang_list = info_languages.get_languages(model)
    typer.echo(info_languages.format_languages(lang_list, pretty=pretty))
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m pytest ../tests/test_info.py -v
```

- [ ] **Step 6: Verify CLI help loads**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m qwen3_tts_cli info --help
cd skill-repo/qwen3-tts/scripts && uv run python -m qwen3_tts_cli info device
```

- [ ] **Step 7: Commit**

```bash
git add skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/info_*.py skill-repo/qwen3-tts/scripts/qwen3_tts_cli/info.py skill-repo/qwen3-tts/tests/test_info.py
git commit -m "feat(qwen3-tts): implement info command group (device, speakers, languages)"
```

---

### Task 7: Implement `generate` command group

**Files:**
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/generate_text.py`
- Create: `skill-repo/qwen3-tts/tests/test_generate.py`
- Modify: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/generate.py`

- [ ] **Step 1: Write failing unit tests**

```python
"""Tests for generate text command logic."""

from unittest.mock import MagicMock, patch
import numpy as np

from qwen3_tts_cli.commands.generate_text import generate_speech


def test_generate_speech_returns_audio_and_sr():
    mock_model = MagicMock()
    mock_model.generate_custom_voice.return_value = ([np.zeros(24000)], 24000)
    audio, sr = generate_speech(
        mock_model,
        text="Hello world",
        language="English",
        speaker="Aiden",
    )
    assert sr == 24000
    assert len(audio) == 24000
    mock_model.generate_custom_voice.assert_called_once_with(
        "Hello world",
        "English",
        "Aiden",
        instruct=None,
    )


def test_generate_speech_with_instruct():
    mock_model = MagicMock()
    mock_model.generate_custom_voice.return_value = ([np.zeros(24000)], 24000)
    generate_speech(
        mock_model,
        text="I can't believe it!",
        language="English",
        speaker="Aiden",
        instruct="Speak with excitement",
    )
    mock_model.generate_custom_voice.assert_called_once_with(
        "I can't believe it!",
        "English",
        "Aiden",
        instruct="Speak with excitement",
    )


def test_generate_speech_defaults_language_to_auto():
    mock_model = MagicMock()
    mock_model.generate_custom_voice.return_value = ([np.zeros(24000)], 24000)
    generate_speech(mock_model, text="Hello", speaker="Aiden")
    call_args = mock_model.generate_custom_voice.call_args
    assert call_args[0][1] == "Auto"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m pytest ../tests/test_generate.py -v
```

- [ ] **Step 3: Implement generate_text logic**

`commands/generate_text.py`:
```python
"""Logic for generate text command — text-to-speech with built-in speakers."""

import numpy as np


def generate_speech(
    model,
    *,
    text: str,
    speaker: str,
    language: str = "Auto",
    instruct: str | None = None,
) -> tuple[np.ndarray, int]:
    """Generate speech from text using a built-in speaker.

    Returns (audio_array, sample_rate).
    """
    wavs, sr = model.generate_custom_voice(
        text,
        language,
        speaker,
        instruct=instruct,
    )
    return wavs[0], sr
```

- [ ] **Step 4: Wire up generate.py thin wrapper**

```python
"""Generate command group — text-to-speech with built-in speakers."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import load_model, save_audio
from .commands import generate_text

generate_app = typer.Typer(help="Text-to-speech generation with built-in speakers.", no_args_is_help=True)
app.add_typer(generate_app, name="generate")


@generate_app.command()
def text(
    content: Annotated[str, typer.Argument(help="Text to synthesize")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")],
    speaker: Annotated[str, typer.Option(help="Built-in speaker name")] = "Aiden",
    instruct: Annotated[Optional[str], typer.Option(help="Style/emotion instruction")] = None,
    lang: Annotated[str, typer.Option(help="Language (English, Chinese, Auto, etc.)")] = "Auto",
    model_size: Annotated[str, typer.Option("--model", help="Model size (1.7b or 0.6b)")] = "1.7b",
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (wav, mp3, flac, ogg)")] = "wav",
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """Generate speech from text using a built-in speaker."""
    model = load_model(model_size, device)
    audio, sr = generate_text.generate_speech(
        model,
        text=content,
        speaker=speaker,
        language=lang,
        instruct=instruct,
    )
    path = save_audio(audio, sr, output, format=format)
    typer.echo(f"Saved to {path}")
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m pytest ../tests/test_generate.py -v
```

- [ ] **Step 6: Commit**

```bash
git add skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/generate_text.py skill-repo/qwen3-tts/scripts/qwen3_tts_cli/generate.py skill-repo/qwen3-tts/tests/test_generate.py
git commit -m "feat(qwen3-tts): implement generate command group"
```

---

### Task 8: Implement `clone` command group

**Files:**
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/clone_text.py`
- Create: `skill-repo/qwen3-tts/tests/test_clone.py`
- Modify: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/clone.py`

- [ ] **Step 1: Write failing unit tests**

```python
"""Tests for clone text command logic."""

from unittest.mock import MagicMock
import numpy as np

from qwen3_tts_cli.commands.clone_text import clone_speech


def test_clone_speech_calls_generate_voice_clone():
    mock_model = MagicMock()
    mock_model.generate_voice_clone.return_value = ([np.zeros(24000)], 24000)
    audio, sr = clone_speech(
        mock_model,
        text="Hello",
        language="English",
        reference="voice.wav",
        ref_text="This is the reference transcript.",
    )
    assert sr == 24000
    mock_model.generate_voice_clone.assert_called_once()
    call_kwargs = mock_model.generate_voice_clone.call_args
    assert call_kwargs[1]["ref_audio"] == "voice.wav"
    assert call_kwargs[1]["ref_text"] == "This is the reference transcript."


def test_clone_speech_defaults_language_to_auto():
    mock_model = MagicMock()
    mock_model.generate_voice_clone.return_value = ([np.zeros(24000)], 24000)
    clone_speech(mock_model, text="Hello", reference="voice.wav", ref_text="text")
    call_args = mock_model.generate_voice_clone.call_args
    assert call_args[1]["language"] == "Auto"


def test_clone_speech_validates_reference_exists():
    import pytest
    mock_model = MagicMock()
    with pytest.raises(FileNotFoundError, match="Reference audio file not found"):
        clone_speech(
            mock_model,
            text="Hello",
            reference="/nonexistent/file.wav",
            ref_text="text",
        )
```

- [ ] **Step 2: Run tests — verify they fail**

- [ ] **Step 3: Implement clone_text logic**

```python
"""Logic for clone text command — voice cloning from reference audio."""

from pathlib import Path

import numpy as np


def clone_speech(
    model,
    *,
    text: str,
    reference: str,
    ref_text: str,
    language: str = "Auto",
) -> tuple[np.ndarray, int]:
    """Clone a voice from reference audio and generate speech.

    Returns (audio_array, sample_rate).
    """
    ref_path = Path(reference)
    if not ref_path.exists():
        raise FileNotFoundError(f"Reference audio file not found: {reference}")

    wavs, sr = model.generate_voice_clone(
        text=text,
        language=language,
        ref_audio=str(ref_path),
        ref_text=ref_text,
    )
    return wavs[0], sr
```

- [ ] **Step 4: Wire up clone.py thin wrapper**

```python
"""Clone command group — voice cloning from reference audio."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import load_model, save_audio
from .commands import clone_text

clone_app = typer.Typer(help="Voice cloning from reference audio.", no_args_is_help=True)
app.add_typer(clone_app, name="clone")


@clone_app.command()
def text(
    content: Annotated[str, typer.Argument(help="Text to synthesize")],
    reference: Annotated[str, typer.Option("--reference", help="Path to reference audio file (3+ seconds)")],
    ref_text: Annotated[str, typer.Option("--ref-text", help="Transcript of the reference audio")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")],
    lang: Annotated[str, typer.Option(help="Language (English, Chinese, Auto, etc.)")] = "Auto",
    model_size: Annotated[str, typer.Option("--model", help="Model size (1.7b or 0.6b)")] = "1.7b",
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (wav, mp3, flac, ogg)")] = "wav",
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """Clone a voice from reference audio and generate speech."""
    model = load_model(model_size, device)
    try:
        audio, sr = clone_text.clone_speech(
            model,
            text=content,
            reference=reference,
            ref_text=ref_text,
            language=lang,
        )
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)
    path = save_audio(audio, sr, output, format=format)
    typer.echo(f"Saved to {path}")
```

- [ ] **Step 5: Run tests — verify they pass**

- [ ] **Step 6: Commit**

```bash
git add skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/clone_text.py skill-repo/qwen3-tts/scripts/qwen3_tts_cli/clone.py skill-repo/qwen3-tts/tests/test_clone.py
git commit -m "feat(qwen3-tts): implement clone command group"
```

---

### Task 9: Implement `design` command group

**Files:**
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/design_text.py`
- Create: `skill-repo/qwen3-tts/tests/test_design.py`
- Modify: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/design.py`

- [ ] **Step 1: Write failing unit tests**

```python
"""Tests for design text command logic."""

from unittest.mock import MagicMock
import numpy as np

from qwen3_tts_cli.commands.design_text import design_speech


def test_design_speech_calls_generate_voice_design():
    mock_model = MagicMock()
    mock_model.generate_voice_design.return_value = ([np.zeros(24000)], 24000)
    audio, sr = design_speech(
        mock_model,
        text="Good morning",
        language="English",
        description="A warm, deep male voice with a calm tone",
    )
    assert sr == 24000
    mock_model.generate_voice_design.assert_called_once_with(
        "Good morning",
        "English",
        "A warm, deep male voice with a calm tone",
    )


def test_design_speech_defaults_language_to_auto():
    mock_model = MagicMock()
    mock_model.generate_voice_design.return_value = ([np.zeros(24000)], 24000)
    design_speech(mock_model, text="Hi", description="warm voice")
    call_args = mock_model.generate_voice_design.call_args
    assert call_args[0][1] == "Auto"


def test_design_speech_requires_description():
    import pytest
    mock_model = MagicMock()
    with pytest.raises(ValueError, match="description"):
        design_speech(mock_model, text="Hi", description="")
```

- [ ] **Step 2: Run tests — verify they fail**

- [ ] **Step 3: Implement design_text logic**

```python
"""Logic for design text command — voice from natural language description."""

import numpy as np


def design_speech(
    model,
    *,
    text: str,
    description: str,
    language: str = "Auto",
) -> tuple[np.ndarray, int]:
    """Design a voice from a description and generate speech.

    Returns (audio_array, sample_rate).
    """
    if not description.strip():
        raise ValueError("Voice description must not be empty")

    wavs, sr = model.generate_voice_design(
        text,
        language,
        description,
    )
    return wavs[0], sr
```

- [ ] **Step 4: Wire up design.py thin wrapper**

```python
"""Design command group — voice design from natural language descriptions."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import load_model, save_audio
from .commands import design_text

design_app = typer.Typer(help="Voice design from natural language descriptions.", no_args_is_help=True)
app.add_typer(design_app, name="design")


@design_app.command()
def text(
    content: Annotated[str, typer.Argument(help="Text to synthesize")],
    description: Annotated[str, typer.Option("--description", help="Natural language voice description")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")],
    lang: Annotated[str, typer.Option(help="Language (English, Chinese, Auto, etc.)")] = "Auto",
    model_size: Annotated[str, typer.Option("--model", help="Model size (1.7b or 0.6b)")] = "1.7b",
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (wav, mp3, flac, ogg)")] = "wav",
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """Design a voice from a natural language description and generate speech."""
    model = load_model(model_size, device)
    try:
        audio, sr = design_text.design_speech(
            model,
            text=content,
            description=description,
            language=lang,
        )
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)
    path = save_audio(audio, sr, output, format=format)
    typer.echo(f"Saved to {path}")
```

- [ ] **Step 5: Run tests — verify they pass**

- [ ] **Step 6: Commit**

```bash
git add skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/design_text.py skill-repo/qwen3-tts/scripts/qwen3_tts_cli/design.py skill-repo/qwen3-tts/tests/test_design.py
git commit -m "feat(qwen3-tts): implement design command group"
```

---

### Task 10: Implement `finetune` command group

**Files:**
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/finetune_prepare.py`
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/finetune_train.py`
- Create: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/finetune_generate.py`
- Create: `skill-repo/qwen3-tts/tests/test_finetune.py`
- Modify: `skill-repo/qwen3-tts/scripts/qwen3_tts_cli/finetune.py`

This is the most complex task. The fine-tuning pipeline uses scripts from the Qwen3-TTS repo. Our CLI wraps the official `sft_12hz.py` script via subprocess (since it's a training script, not a library function).

- [ ] **Step 1: Write failing unit tests**

```python
"""Tests for finetune command logic."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

from qwen3_tts_cli.commands.finetune_prepare import validate_audio_dir
from qwen3_tts_cli.commands.finetune_train import build_train_args
from qwen3_tts_cli.commands.finetune_generate import generate_from_finetuned


def test_validate_audio_dir_with_wav_files(tmp_path):
    (tmp_path / "sample1.wav").write_bytes(b"RIFF" + b"\x00" * 100)
    (tmp_path / "sample2.wav").write_bytes(b"RIFF" + b"\x00" * 100)
    result = validate_audio_dir(str(tmp_path))
    assert result["wav_count"] == 2
    assert result["valid"] is True


def test_validate_audio_dir_empty(tmp_path):
    result = validate_audio_dir(str(tmp_path))
    assert result["wav_count"] == 0
    assert result["valid"] is False


def test_validate_audio_dir_nonexistent():
    with pytest.raises(FileNotFoundError):
        validate_audio_dir("/nonexistent/dir")


def test_build_train_args_defaults():
    args = build_train_args(
        dataset="/data/train.jsonl",
        output_dir="/output/model",
        base_model="1.7b",
    )
    assert "--init_model_path" in args
    assert "Qwen/Qwen3-TTS-12Hz-1.7B-Base" in args
    assert "--output_model_path" in args
    assert "/output/model" in args
    assert "--train_jsonl" in args
    assert "/data/train.jsonl" in args


def test_build_train_args_custom_epochs():
    args = build_train_args(
        dataset="/data/train.jsonl",
        output_dir="/output",
        base_model="0.6b",
        epochs=20,
        batch_size=16,
    )
    idx = args.index("--num_epochs")
    assert args[idx + 1] == "20"
    idx = args.index("--batch_size")
    assert args[idx + 1] == "16"
    assert "Qwen/Qwen3-TTS-12Hz-0.6B-Base" in args


def test_generate_from_finetuned():
    mock_model = MagicMock()
    mock_model.generate_custom_voice.return_value = ([np.zeros(24000)], 24000)
    audio, sr = generate_from_finetuned(
        model=mock_model,
        text="Hello",
        language="English",
    )
    assert sr == 24000
    assert len(audio) == 24000
```

- [ ] **Step 2: Run tests — verify they fail**

- [ ] **Step 3: Implement finetune logic modules**

`commands/finetune_prepare.py`:
```python
"""Logic for finetune prepare command — validate and prepare training data."""

from pathlib import Path


def validate_audio_dir(audio_dir: str) -> dict:
    """Validate an audio directory has WAV files for training.

    Returns a dict with validation results.
    """
    path = Path(audio_dir)
    if not path.exists():
        raise FileNotFoundError(f"Audio directory not found: {audio_dir}")

    wav_files = list(path.glob("*.wav"))
    return {
        "audio_dir": str(path),
        "wav_count": len(wav_files),
        "valid": len(wav_files) > 0,
        "files": [f.name for f in wav_files],
    }
```

`commands/finetune_train.py`:
```python
"""Logic for finetune train command — build training arguments."""

from ..backend import base_model_name_from_size


def build_train_args(
    *,
    dataset: str,
    output_dir: str,
    base_model: str = "1.7b",
    epochs: int | None = None,
    batch_size: int | None = None,
    learning_rate: float | None = None,
    speaker_name: str = "custom_speaker",
) -> list[str]:
    """Build argument list for the fine-tuning script.

    Returns args for `python sft_12hz.py <args>`.
    """
    model_name = base_model_name_from_size(base_model)
    args = [
        "--init_model_path", model_name,
        "--output_model_path", output_dir,
        "--train_jsonl", dataset,
        "--speaker_name", speaker_name,
    ]

    if epochs is not None:
        args.extend(["--num_epochs", str(epochs)])
    if batch_size is not None:
        args.extend(["--batch_size", str(batch_size)])
    if learning_rate is not None:
        args.extend(["--lr", str(learning_rate)])

    return args
```

`commands/finetune_generate.py`:
```python
"""Logic for finetune generate command — generate from a fine-tuned model."""

import numpy as np


def generate_from_finetuned(
    model,
    *,
    text: str,
    language: str = "Auto",
    instruct: str | None = None,
) -> tuple[np.ndarray, int]:
    """Generate speech from a fine-tuned model.

    Fine-tuned models are single-speaker, so no speaker parameter.
    Returns (audio_array, sample_rate).
    """
    wavs, sr = model.generate_custom_voice(
        text,
        language,
        "custom_speaker",
        instruct=instruct,
    )
    return wavs[0], sr
```

- [ ] **Step 4: Wire up finetune.py thin wrapper**

```python
"""Finetune command group — custom voice model training pipeline."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import save_audio
from .commands import finetune_prepare, finetune_train, finetune_generate

finetune_app = typer.Typer(help="Fine-tune custom voice models.", no_args_is_help=True)
app.add_typer(finetune_app, name="finetune")


@finetune_app.command()
def prepare(
    audio_dir: Annotated[str, typer.Option("--audio-dir", help="Directory of WAV files")],
    output_dir: Annotated[str, typer.Option("--output-dir", help="Where to write prepared dataset")],
    lang: Annotated[str, typer.Option(help="Language of the audio")] = "en",
) -> None:
    """Prepare training data from audio files."""
    import json

    try:
        result = finetune_prepare.validate_audio_dir(audio_dir)
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    if not result["valid"]:
        typer.echo(f"ERROR: No WAV files found in {audio_dir}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Found {result['wav_count']} WAV files in {audio_dir}")
    typer.echo(json.dumps(result, indent=2))
    typer.echo(f"\nDataset preparation would write to: {output_dir}")
    typer.echo("NOTE: Full dataset preparation requires the Qwen3-TTS finetuning scripts.")


@finetune_app.command()
def train(
    dataset: Annotated[str, typer.Option("--dataset", help="Path to prepared training JSONL")],
    output_dir: Annotated[str, typer.Option("--output-dir", help="Where to save trained model")],
    base_model: Annotated[str, typer.Option("--base-model", help="Base model size (1.7b or 0.6b)")] = "1.7b",
    epochs: Annotated[Optional[int], typer.Option(help="Number of training epochs")] = None,
    batch_size: Annotated[Optional[int], typer.Option(help="Training batch size")] = None,
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu)")] = None,
) -> None:
    """Train a custom voice model."""
    args = finetune_train.build_train_args(
        dataset=dataset,
        output_dir=output_dir,
        base_model=base_model,
        epochs=epochs,
        batch_size=batch_size,
    )
    typer.echo(f"Training args: {' '.join(args)}")
    typer.echo("NOTE: Run the actual training via the Qwen3-TTS finetuning scripts.")


@finetune_app.command("generate")
def generate_cmd(
    content: Annotated[str, typer.Argument(help="Text to synthesize")],
    model_dir: Annotated[str, typer.Option("--model-dir", help="Path to fine-tuned model directory")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")],
    instruct: Annotated[Optional[str], typer.Option(help="Style/emotion instruction")] = None,
    lang: Annotated[str, typer.Option(help="Language")] = "Auto",
    format: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "wav",
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """Generate speech using a fine-tuned model."""
    from qwen_tts import Qwen3TTSModel
    import torch
    from ..backend import detect_device

    dev = detect_device(device)
    dtype = torch.bfloat16 if dev != "cpu" else torch.float32
    model = Qwen3TTSModel.from_pretrained(
        model_dir,
        device_map=f"{dev}:0" if dev == "cuda" else dev,
        dtype=dtype,
    )
    audio, sr = finetune_generate.generate_from_finetuned(
        model,
        text=content,
        language=lang,
        instruct=instruct,
    )
    path = save_audio(audio, sr, output, format=format)
    typer.echo(f"Saved to {path}")
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m pytest ../tests/ -v
```

Expected: All tests across all modules PASS.

- [ ] **Step 6: Commit**

```bash
git add skill-repo/qwen3-tts/scripts/qwen3_tts_cli/commands/finetune_*.py skill-repo/qwen3-tts/scripts/qwen3_tts_cli/finetune.py skill-repo/qwen3-tts/tests/test_finetune.py
git commit -m "feat(qwen3-tts): implement finetune command group"
```

---

## Phase 4: Integration Testing and Verification

### Task 11: Write Tier 2 integration tests

**Files:**
- Create: `qa/qwen3-tts/__init__.py`
- Create: `qa/qwen3-tts/test_integration.py`

- [ ] **Step 1: Write integration tests**

These tests require the real qwen-tts model and GPU. They use the 0.6B model for speed.

```python
"""Tier 2: Integration tests for qwen3-tts against real model.

These tests load the real model and generate audio.
Skips if qwen-tts is not installed or no GPU available.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "skill-repo" / "qwen3-tts" / "scripts")
)


@pytest.fixture(scope="module")
def tts_model():
    """Load the 0.6B model for integration tests. Skip if unavailable."""
    try:
        import torch
        from qwen_tts import Qwen3TTSModel
    except ImportError:
        pytest.skip("qwen-tts not installed")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        pytest.skip("Integration tests require GPU")

    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    return model


@pytest.mark.integration
class TestGenerateIntegration:
    def test_basic_tts(self, tts_model, tmp_path):
        from qwen3_tts_cli.commands.generate_text import generate_speech
        audio, sr = generate_speech(
            tts_model,
            text="Hello world",
            speaker="Aiden",
            language="English",
        )
        assert sr > 0
        assert len(audio) > sr  # at least 1 second of audio

        import soundfile as sf
        out = tmp_path / "test.wav"
        sf.write(str(out), audio, sr)
        assert out.stat().st_size > 10_000

    def test_tts_with_instruct(self, tts_model, tmp_path):
        from qwen3_tts_cli.commands.generate_text import generate_speech
        audio, sr = generate_speech(
            tts_model,
            text="I cannot believe it!",
            speaker="Aiden",
            language="English",
            instruct="Speak with excitement",
        )
        assert len(audio) > 0


@pytest.mark.integration
class TestInfoIntegration:
    def test_speakers_returns_list(self, tts_model):
        speakers = tts_model.get_supported_speakers()
        assert isinstance(speakers, list)
        assert len(speakers) > 0
        assert all(isinstance(s, str) for s in speakers)

    def test_languages_returns_list(self, tts_model):
        languages = tts_model.get_supported_languages()
        assert isinstance(languages, list)
        assert len(languages) > 0
```

- [ ] **Step 2: Run integration tests**

```bash
cd E:/workspaces/tools/cli-me && uv run pytest qa/qwen3-tts/test_integration.py -v -m integration
```

Expected: PASS if GPU available, SKIP if not.

- [ ] **Step 3: Commit**

```bash
git add qa/qwen3-tts/
git commit -m "test(qwen3-tts): add Tier 2 integration tests"
```

---

### Task 12: Final verification and smoke test

- [ ] **Step 1: Run all unit tests**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m pytest ../tests/ -v
```

- [ ] **Step 2: Run all QA tests**

```bash
cd E:/workspaces/tools/cli-me && uv run pytest qa/qwen3-tts/ -v
```

- [ ] **Step 3: Verify CLI loads all commands**

```bash
cd skill-repo/qwen3-tts/scripts && uv run python -m qwen3_tts_cli --help
uv run python -m qwen3_tts_cli generate --help
uv run python -m qwen3_tts_cli clone --help
uv run python -m qwen3_tts_cli design --help
uv run python -m qwen3_tts_cli info --help
uv run python -m qwen3_tts_cli finetune --help
```

- [ ] **Step 4: Live smoke test (if GPU available)**

```bash
uv run python -m qwen3_tts_cli info device
uv run python -m qwen3_tts_cli generate text "Hello, I am Qwen three TTS" --speaker Aiden -o /tmp/hello.wav
uv run python -m qwen3_tts_cli info speakers --pretty
```

- [ ] **Step 5: Update wiki log**

```bash
clime log append --skill qwen3-tts --message "2026-04-16: Initial implementation complete. 5 command groups: generate, clone, design, info, finetune. All unit tests passing." --log-file skill-repo/qwen3-tts/references/log.md
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(qwen3-tts): complete initial implementation with all 5 command groups"
```
