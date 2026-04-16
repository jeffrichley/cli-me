---
title: Basic Text-to-Speech
tags: [technique, qwen3-tts, basic, generation]
sources: [https://github.com/QwenLM/Qwen3-TTS, https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base]
created: 2026-04-16
updated: 2026-04-16
---

# Basic Text-to-Speech

## When to Use

- Generating narration, podcast audio, or audiobook content from a script
- Producing voiceover for a known built-in speaker personality
- Quick prototyping before committing to voice cloning or voice design

## Technique

The CustomVoice model variants (`Qwen3-TTS-12Hz-1.7B-CustomVoice`, `Qwen3-TTS-12Hz-0.6B-CustomVoice`) are designed for basic TTS. They accept a speaker name and optional style instruction, making them the simplest entry point.

Load the model once and reuse it across all generations. Loading is expensive (model weights + speech tokenizer); synthesis itself is comparatively fast once loaded.

Output is always a `float32` numpy array at **24kHz**. Save it directly with `soundfile`. The CLI's `--format` flag (e.g., `--format mp3`) handles format conversion natively via `save_audio()` — no manual ffmpeg conversion is needed.

## CLI Commands

Generate a single line with the default speaker:

```bash
uv run python -m qwen3_tts_cli generate text "Hello, world!" -o hello.wav
```

Choose a specific speaker:

```bash
uv run python -m qwen3_tts_cli generate text "Welcome to the show." --speaker Aiden -o welcome.wav
```

Convert output to MP3 using the `--format` flag (no ffmpeg required):

```bash
uv run python -m qwen3_tts_cli generate text "This will be an MP3." --speaker Ryan --format mp3 -o output.mp3
```

List all available speakers:

```bash
uv run python -m qwen3_tts_cli info speakers --pretty
```

## Under the Hood

1. Text is tokenized by `AutoProcessor` into `input_ids`.
2. `model.generate()` runs the 1.7B (or 0.6B) transformer in a causal LM style, producing a sequence of discrete codec tokens rather than text tokens. The 12Hz tokenizer uses 16 codebooks, each with 2048 entries, at 12.5 frames/sec.
3. Codec tokens are decoded by the `Qwen3TTSTokenizer` (12Hz vocoder) into a float32 waveform at 24kHz.
4. The result is a 1-D numpy array returned alongside the sample rate integer.

The Dual-Track architecture generates a "main talker" track and a "sub-talker" refinement track. Both are controlled by sampling parameters (`temperature`, `top_k`, etc.), so generation is non-deterministic by default.

## Gotchas

- Output is always **24kHz**. Use `--format mp3` (or other formats) via the CLI to get non-WAV output — the `save_audio()` backend handles this natively.
- Speaker names are validated case-insensitively. Passing an unsupported name raises a `ValueError` listing valid options.
- CPU inference is extremely slow (minutes per sentence). A CUDA GPU is strongly recommended.
- Model weights download on first use (~3.4GB for 1.7B, ~1.2GB for 0.6B). Ensure sufficient disk space and a stable network connection.
- The `sox` binary produces a "not found" warning during startup — this is non-fatal and does not affect output quality.
- Generation is non-deterministic. The same text and speaker will produce slightly different audio each run due to sampling.

## Sources

- https://github.com/QwenLM/Qwen3-TTS
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice

## Learned from Usage

(No usage notes yet.)
