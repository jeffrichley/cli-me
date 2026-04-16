---
title: Known Gotchas and Pitfalls
tags: [gotchas, qwen3-tts]
created: 2026-04-16
updated: 2026-04-16
---

# Known Gotchas and Pitfalls

A consolidated list of non-obvious issues discovered during research and usage. See individual technique pages for context-specific gotchas.

---

## Installation and First Use

### Model downloads on first use

Model weights are downloaded from Hugging Face Hub the first time `from_pretrained` is called with a Hub model ID. This requires a network connection and free disk space:

- **1.7B variants** (CustomVoice, VoiceDesign, Base): approximately **3.4GB each**
- **0.6B variants** (CustomVoice, Base): approximately **1.2GB each**
- **12Hz Tokenizer** (shared component): approximately **500MB**

Plan for this in CI/CD or deployment environments. Pre-download with `huggingface-cli download` or set `HF_HUB_OFFLINE=1` after caching.

### `sox` binary not found warning is non-fatal

During model loading, the `sox` Python package attempts to locate the `sox` system binary. If it is not installed, a warning is printed to stderr. **This does not affect synthesis output.** The warning can be safely ignored. Install `sox` system package to suppress it if desired.

### `flash-attn` is not required but recommended

The `flash-attn` package is not listed in `pyproject.toml` and is not installed by default. The model runs correctly without it using standard PyTorch attention. To enable Flash Attention 2 for faster inference on Ampere+ GPUs, install it separately:

```bash
pip install flash-attn --no-build-isolation
```

Then pass `attn_implementation="flash_attention_2"` to `from_pretrained`.

---

## CLI and Interface

### No native CLI — we wrap the Python API directly

The official `qwen-tts` package (v0.1.1) ships only a Gradio web UI demo (`qwen-tts-demo`). There is no official scriptable command-line tool. A third-party `qwen-tts-cli` package exists on PyPI but is not maintained by Qwen and is not used by this skill.

Our skill wraps the Python API (`Qwen3TTSModel`) directly.

### Agent context has no stdin — no interactive prompts possible

When running inside Claude Code (agent mode), there is no interactive terminal. Any code path that calls `input()` or otherwise reads from stdin will hang indefinitely or raise an error. The `qwen-tts-demo` Gradio UI is not usable in this context for the same reason. All interaction must go through the CLI arguments we design.

---

## Inference Behavior

### CPU inference is very slow

Running synthesis on CPU is technically supported but produces results in minutes per sentence rather than seconds. Use a CUDA GPU for all practical work. The 0.6B model is the only viable option if GPU VRAM is severely constrained.

### Output is always 24kHz

The 12Hz tokenizer's vocoder outputs at **24000 Hz** regardless of model size, dtype, or generation parameters. There is no output sample rate configuration. If a different sample rate is needed, resample the output waveform after generation (e.g., with `librosa.resample` or `torchaudio.transforms.Resample`).

### Generation is non-deterministic by default

The model uses sampling (`do_sample=True`, `temperature=0.9`) by default. The same text, speaker, and language will produce slightly different audio each run. For reproducibility, set a fixed random seed via PyTorch before generating: `torch.manual_seed(42)`.

---

## Model Variant Restrictions

### Each method requires a specific model type

| Method                  | Required model type      |
|-------------------------|--------------------------|
| `generate_custom_voice` | `custom_voice`           |
| `generate_voice_clone`  | `base`                   |
| `generate_voice_design` | `voice_design`           |

Calling the wrong method for the loaded model raises an error. The skill CLI must load the correct model variant for the requested command.

### `instruct` is silently ignored on 0.6B CustomVoice

The 0.6B CustomVoice model does not have the capacity to act on instruct tokens. The wrapper detects `tts_model_size == "0b6"` and sets `instruct=None` without raising an error or warning. If style guidance is required, use the 1.7B CustomVoice model.

---

## Voice Cloning Specifics

### `numpy.ndarray` alone is not a valid `AudioLike`

The `AudioLike` type accepts `(np.ndarray, sample_rate)` tuples, not bare numpy arrays. Passing a bare array raises a `ValueError`. Always wrap: `(audio_array, sample_rate)`.

### Reference transcript must match audio exactly

In ICL mode (`x_vector_only_mode=False`), mismatches between `ref_text` and the actual audio content degrade voice cloning quality significantly. Punctuation, contractions, and spacing all matter.

---

## Learned from Usage

(No usage notes yet.)
