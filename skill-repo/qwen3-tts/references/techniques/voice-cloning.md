---
title: Voice Cloning
tags: [technique, qwen3-tts, voice-cloning, reference-audio]
sources: [https://github.com/QwenLM/Qwen3-TTS, https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base]
created: 2026-04-16
updated: 2026-04-16
---

# Voice Cloning

## When to Use

- Reproducing a specific person's voice that is not among the built-in speakers
- Preserving an existing recorded voice style across many generated lines
- Creating a consistent custom voice from a short audio sample (e.g., for a game character or brand narrator)
- Generating audio that matches a client's own voice

## Technique

Voice cloning is only available on the **Base model variants** (`Qwen3-TTS-12Hz-1.7B-Base`, `Qwen3-TTS-12Hz-0.6B-Base`). The CustomVoice and VoiceDesign models do not support it.

The model uses **in-context learning (ICL)**: it receives the reference audio as codec tokens prepended to the synthesis context, essentially "showing" the model how the target voice sounds before generating new speech. This is why the reference transcript (`ref_text`) is required for highest quality — without it, the model cannot align the reference tokens to phonemic content.

There are two cloning modes:

**ICL mode (default, higher quality):** Both reference audio and its exact transcript are provided. The model learns prosody, timber, and rhythm from the audio-text alignment. Use this whenever you can transcribe the reference audio accurately.

**X-vector-only mode:** Only the speaker embedding (extracted by the ECAPA-TDNN encoder) is used. The transcript is not needed, but naturalness and similarity are typically lower. Use when the reference audio cannot be reliably transcribed.

For generating many lines from the same speaker, pre-compute the voice clone prompt once with `create_voice_clone_prompt()` and reuse it. This avoids re-encoding the reference audio on every call.

Reference audio quality matters significantly. Aim for:
- **Minimum 3 seconds** of continuous speech
- **Single speaker** — no background voices or music
- **Clean audio** — minimal noise, reverb, or room echo
- The transcript must match the audio **exactly** — mismatches degrade quality

## CLI Commands

Clone a voice from a reference audio file:

```bash
python qwen3_tts_cli.py clone text "The quick brown fox jumped over the lazy dog." \
  --reference voice_sample.wav \
  --ref-text "Hello, my name is Alex and this is my voice." \
  -o output.wav
```

Clone using x-vector-only mode (no transcript needed):

```bash
python qwen3_tts_cli.py clone text "Some text to synthesize." \
  --reference voice_sample.wav \
  --x-vector-only \
  -o output.wav
```

Clone from a URL reference:

```bash
python qwen3_tts_cli.py clone text "Text to synthesize." \
  --reference "https://example.com/speaker_sample.wav" \
  --ref-text "This is what the speaker says in the sample." \
  -o output.wav
```

## Under the Hood

1. The reference audio is loaded and normalized (resampled to 24kHz mono if needed).
2. The ECAPA-TDNN speaker encoder extracts a speaker embedding (`ref_spk_embedding`) from the reference audio.
3. In ICL mode, the reference audio is also encoded into codec tokens (`ref_code`) by the 12Hz speech tokenizer.
4. At generation time, the `ref_code` is prepended to the synthesis context so the model can attend to the reference voice's codec pattern.
5. After decoding, the reference portion is trimmed from the output waveform, returning only the newly synthesized speech.
6. The pre-built `VoiceClonePromptItem` holds: `ref_code`, `ref_spk_embedding`, `x_vector_only_mode`, `icl_mode`, and `ref_text`. These are all the ingredients needed to skip re-encoding on subsequent calls.

Audio input is normalized via `_normalize_audio_inputs`. Multi-channel audio is averaged to mono before processing.

## Gotchas

- **Base model only.** Attempting voice clone on a CustomVoice or VoiceDesign model will raise an error.
- **Transcript must match exactly.** Even small mismatches (punctuation, contractions) cause noticeable quality degradation.
- **Minimum 3 seconds of reference audio.** Very short clips produce inconsistent speaker embedding extraction.
- **numpy array alone is not a valid `AudioLike`.** You must wrap it as a `(array, sample_rate)` tuple.
- **x-vector-only mode loses naturalness.** The speaker embedding captures timbre but not prosodic patterns. Use ICL mode whenever possible.
- `voice_clone_prompt` is not serializable to JSON — it is a Python object. You cannot persist it across processes without custom serialization.
- Noisy or reverberant reference audio will produce noisy output. The model inherits artefacts from the reference.
- Using a reference recorded at a different sample rate is fine — the wrapper resamples automatically. But recording quality still matters.

## Sources

- https://github.com/QwenLM/Qwen3-TTS
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base

## Learned from Usage

(No usage notes yet.)
