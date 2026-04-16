---
title: Research and Development Log
tags: [log, qwen3-tts]
created: 2026-04-16
updated: 2026-04-16
---

# Research and Development Log

## 2026-04-16: Initial research completed

Analyzed Qwen3-TTS v0.1.1 (commit `022e286`, message: "fix finetuning bug") cloned from https://github.com/QwenLM/Qwen3-TTS.

Created source analysis pages:
- `source-analysis/analyzed-version.md` — package version, dependencies, Python requirements
- `source-analysis/api-surface.md` — full `Qwen3TTSModel` API, speaker table, language table, type aliases
- `source-analysis/cli-interface.md` — no native scriptable CLI; Gradio demo only; third-party CLI not used
- `source-analysis/internal-architecture.md` — Dual-Track architecture, component breakdown, inference pipelines
- `source-analysis/key-functions.md` — generation kwargs, speech tokenizer, fine-tuning entry points, audio normalization

Created technique pages:
- `techniques/basic-tts.md` — CustomVoice model, speaker selection, output formats, batch generation
- `techniques/voice-cloning.md` — Base model, ICL vs x-vector, reference audio requirements, prompt reuse
- `techniques/voice-design.md` — VoiceDesign model, description writing, supported attributes
- `techniques/speaker-styles.md` — 9 built-in speakers, instruct parameter, 0.6B limitation
- `techniques/multilingual.md` — 10 languages, Auto detection, batch language lists
- `techniques/fine-tuning.md` — prepare_data.py → sft_12hz.py pipeline, hardware requirements
- `techniques/gpu-optimization.md` — VRAM tables, bfloat16, Flash Attention 2, CPU fallback, batching

Created operational files:
- `index.md` — full table of contents
- `log.md` — this file
- `gotchas.md` — known issues and non-obvious pitfalls
