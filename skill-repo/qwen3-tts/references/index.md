---
title: Qwen3-TTS References Index
tags: [index, qwen3-tts]
created: 2026-04-16
updated: 2026-04-16
---

# Qwen3-TTS References Index

This directory contains source analysis pages (written from the analyzed codebase) and technique pages (how-to guides for building the skill).

---

## Source Analysis

These pages document what the analyzed source code actually does. Created from commit `022e286` of https://github.com/QwenLM/Qwen3-TTS, package version `0.1.1`.

| Page | Contents |
|------|----------|
| [analyzed-version.md](source-analysis/analyzed-version.md) | Exact version, commit, dependencies, Python requirements |
| [api-surface.md](source-analysis/api-surface.md) | All public methods on `Qwen3TTSModel`, type aliases, speaker and language tables |
| [cli-interface.md](source-analysis/cli-interface.md) | Why there is no native scriptable CLI; how our skill wraps the Python API |
| [internal-architecture.md](source-analysis/internal-architecture.md) | Dual-Track architecture, component breakdown, inference pipelines, output format |
| [key-functions.md](source-analysis/key-functions.md) | Generation kwargs, speech tokenizer methods, fine-tuning entry points, audio normalization |

---

## Techniques

How-to guides for common synthesis tasks. These reference the planned CLI syntax (`qwen3_tts_cli.py`) that will be implemented in later tasks.

| Page | Contents |
|------|----------|
| [techniques/basic-tts.md](techniques/basic-tts.md) | Loading the model, choosing a speaker, output formats, batch generation |
| [techniques/voice-cloning.md](techniques/voice-cloning.md) | Reference audio requirements, ICL vs x-vector modes, `AudioLike` input types, reusing prompts |
| [techniques/voice-design.md](techniques/voice-design.md) | Writing effective voice descriptions, supported attributes, limitations |
| [techniques/speaker-styles.md](techniques/speaker-styles.md) | The 9 built-in speakers, model variant support, `instruct` parameter guidance |
| [techniques/multilingual.md](techniques/multilingual.md) | 10 supported languages, auto-detection, explicit selection, batch language lists |
| [techniques/fine-tuning.md](techniques/fine-tuning.md) | Full pipeline: prepare → encode → train; hardware requirements; using fine-tuned models |
| [techniques/gpu-optimization.md](techniques/gpu-optimization.md) | VRAM requirements, bfloat16, Flash Attention 2, CPU fallback, batch throughput |

---

## Operational

| Page | Contents |
|------|----------|
| [log.md](log.md) | Research and development log |
| [gotchas.md](gotchas.md) | Known issues and non-obvious pitfalls |
