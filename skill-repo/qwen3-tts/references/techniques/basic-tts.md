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
- Batch-generating multiple lines of audio in a single run
- Quick prototyping before committing to voice cloning or voice design

## Technique

The CustomVoice model variants (`Qwen3-TTS-12Hz-1.7B-CustomVoice`, `Qwen3-TTS-12Hz-0.6B-CustomVoice`) are designed for basic TTS. They accept a speaker name and optional style instruction, making them the simplest entry point.

Load the model once and reuse it across all generations. Loading is expensive (model weights + speech tokenizer); synthesis itself is comparatively fast once loaded.

Output is always a `float32` numpy array at **24kHz**. Save it directly with `soundfile`; for MP3 or other formats, pipe through `ffmpeg` after writing the WAV.

Batch generation (passing a list of strings) is more efficient than calling generate repeatedly because it amortizes GPU overhead. Use it whenever you have multiple lines to synthesize.

## CLI Commands

Generate a single line with the default speaker:

```bash
python qwen3_tts_cli.py generate text "Hello, world!" -o hello.wav
```

Choose a specific speaker:

```bash
python qwen3_tts_cli.py generate text "Welcome to the show." --speaker Aiden -o welcome.wav
```

Convert output to MP3 using ffmpeg after generation:

```bash
python qwen3_tts_cli.py generate text "This will be an MP3." --speaker Ryan -o tmp.wav
ffmpeg -i tmp.wav -q:a 2 output.mp3
```

List all available speakers:

```bash
python qwen3_tts_cli.py info speakers --pretty
```

Batch generate from a text file (one line per output):

```bash
python qwen3_tts_cli.py generate text "Line one." "Line two." "Line three." --speaker Serena -o batch_output/
```

## Under the Hood

1. Text is tokenized by `AutoProcessor` into `input_ids`.
2. `model.generate()` runs the 1.7B (or 0.6B) transformer in a causal LM style, producing a sequence of discrete codec tokens rather than text tokens. The 12Hz tokenizer uses 16 codebooks, each with 2048 entries, at 12.5 frames/sec.
3. Codec tokens are decoded by the `Qwen3TTSTokenizer` (12Hz vocoder) into a float32 waveform at 24kHz.
4. The result is a 1-D numpy array — one per batch item — returned alongside the sample rate integer.

The Dual-Track architecture generates a "main talker" track and a "sub-talker" refinement track. Both are controlled by sampling parameters (`temperature`, `top_k`, etc.), so generation is non-deterministic by default.

## Gotchas

- Output is always **24kHz WAV** (float32 numpy). There is no native MP3/OGG output — convert with ffmpeg.
- Speaker names are validated case-insensitively. Passing an unsupported name raises a `ValueError` listing valid options.
- `max_new_tokens=2048` is the default. Long texts may be truncated. For texts exceeding ~30 seconds of speech, increase this via `--max-new-tokens`.
- CPU inference is extremely slow (minutes per sentence). A CUDA GPU is strongly recommended.
- Model weights download on first use (~3.4GB for 1.7B, ~1.2GB for 0.6B). Ensure sufficient disk space and a stable network connection.
- The `sox` binary produces a "not found" warning during startup — this is non-fatal and does not affect output quality.
- Generation is non-deterministic. The same text and speaker will produce slightly different audio each run due to sampling.

## Sources

- https://github.com/QwenLM/Qwen3-TTS
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice

## Learned from Usage

(No usage notes yet.)
