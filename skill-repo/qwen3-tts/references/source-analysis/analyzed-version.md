---
title: Analyzed Version
tags: [source-analysis, qwen3-tts]
sources: [https://github.com/QwenLM/Qwen3-TTS]
created: 2026-04-16
updated: 2026-04-16
---

# Analyzed Version

## Source Repository

- **URL**: https://github.com/QwenLM/Qwen3-TTS
- **Git commit analyzed**: `022e286` (message: "fix finetuning bug")
- **Clone date**: 2026-04-16

## Package Version

- **PyPI package name**: `qwen-tts`
- **Version**: `0.1.1`
- **Source**: `pyproject.toml` in the cloned repo

## Key Release Date

- Announced 2026-01-22 per README NEWS section.
- Paper: arXiv:2601.15621 (Qwen3-TTS Technical Report)

## Python Requirements

- Python >= 3.9
- Tested on 3.9, 3.10, 3.11, 3.12, 3.13

## Core Dependencies (from pyproject.toml)

```
transformers==4.57.3
accelerate==1.12.0
gradio
librosa
torchaudio
soundfile
sox
onnxruntime
einops
```

## Notes

- The `qwen-tts-demo` CLI entry point is the Gradio web UI demo, not a programmatic CLI.
- There is no native batch/scriptable CLI in this package — our skill wraps the Python API.
- Optional performance dep: `flash-attn` (not in pyproject.toml, installed separately).
