---
title: Internal Architecture
tags: [source-analysis, qwen3-tts]
sources: [https://github.com/QwenLM/Qwen3-TTS]
created: 2026-04-16
updated: 2026-04-16
---

# Internal Architecture

## High-Level Overview

Qwen3-TTS uses a **discrete multi-codebook language model** architecture. It bypasses
the traditional LM+DiT (Diffusion Transformer) cascade by doing full end-to-end
speech modeling with a single LM. This is described as a "Dual-Track hybrid streaming
generation architecture."

```
Text input
    ↓
Text Tokenizer / Processor  (AutoProcessor → Qwen3TTSProcessor)
    ↓
Talker LM  (Qwen3TTS transformer, 0.6B or 1.7B parameters)
    ↓  generates codec token sequences
Speech Tokenizer / Vocoder  (Qwen3-TTS-Tokenizer-12Hz)
    ↓  decodes codec tokens back to waveform
Audio output (float32 numpy array)
```

## Core Components

### 1. Qwen3TTSModel (wrapper)

`qwen_tts/inference/qwen3_tts_model.py`

High-level Python API. Handles:
- Model + processor loading via `AutoModel` / `AutoProcessor`
- Audio input normalization (path/URL/base64/numpy)
- Language and speaker validation
- Generation kwargs merging with `generate_config.json` defaults
- Batching logic for all three generation modes

### 2. Qwen3TTSForConditionalGeneration (core model)

`qwen_tts/core/models/modeling_qwen3_tts.py`

The HuggingFace `PreTrainedModel` subclass. Key attributes set at load time:
- `self.tts_model_type` — `"base"`, `"custom_voice"`, or `"voice_design"`
- `self.tts_model_size` — `"0b6"` or `"1b7"`
- `self.tokenizer_type` — e.g. `"v2"` (12Hz tokenizer)
- `self.speech_tokenizer` — `Qwen3TTSTokenizer` instance (loaded from `speech_tokenizer/` subfolder)
- `self.speaker_encoder_sample_rate` — from config (24000 Hz per `configuration_qwen3_tts.py`)
- `self.generate_config` — dict loaded from `generate_config.json` in the model checkpoint
- `self.supported_speakers` — list of valid speaker names (CustomVoice models)
- `self.supported_languages` — list of valid language names

Exposes:
- `model.generate(input_ids, ...)` — HuggingFace GenerationMixin generate
- `model.extract_speaker_embedding(audio, sr)` — ECAPA-TDNN speaker encoder
- `model.speech_tokenizer.encode(...)` — encode audio to codec codes
- `model.speech_tokenizer.decode(...)` — decode codec codes to waveform
- `model.get_supported_speakers()` → `list | None`
- `model.get_supported_languages()` → `list | None`

### 3. Speech Tokenizer (Qwen3-TTS-Tokenizer-12Hz)

`qwen_tts/inference/qwen3_tts_tokenizer.py`
`qwen_tts/core/tokenizer_12hz/`

The 12Hz tokenizer produces **16 codebooks** with codebook size **2048** at **12.5 frames/sec**.
It is a separate model loaded from `speech_tokenizer/` within the main model directory.

Key methods on `Qwen3TTSTokenizer`:
- `encode(audio, sr)` → `ModelOutput` with `audio_codes` field
- `decode(encoded)` → `(List[np.ndarray], int)` — waveform(s) + sample rate
- `get_input_sample_rate()` → int
- `get_output_sample_rate()` → int (the output WAV sample rate)
- `get_encode_downsample_rate()` → int
- `get_decode_upsample_rate()` → int

Output sample rate is determined at runtime by calling `model.get_output_sample_rate()`.
The 12Hz tokenizer family outputs at a high-fidelity rate — exact value depends on the
checkpoint's vocoder config but is typically **24000 Hz**.

### 4. Speaker Encoder (ECAPA-TDNN)

Embedded in `Qwen3TTSForConditionalGeneration`. Used only by Base models for voice cloning.

Architecture blocks visible in source:
- `TimeDelayNetBlock` — dilated Conv1d + ReLU
- `Res2NetBlock` — multi-scale grouped convolutions
- `SqueezeExcitationBlock` — channel attention
- `SqueezeExcitationRes2NetBlock` — TDNN-Res2Net-TDNN-SE building block (ECAPA-TDNN)
- `AttentiveStatisticsPooling` — attentive mean+std pooling to get utterance embedding

Speaker encoder input sample rate: **24000 Hz** (audio is resampled before embedding extraction).

## Model Variants and Capabilities

| Model ID | Type | Size | Instruct | Voice Clone |
|---|---|---|---|---|
| Qwen3-TTS-12Hz-1.7B-CustomVoice | custom_voice | 1b7 | yes | no |
| Qwen3-TTS-12Hz-0.6B-CustomVoice | custom_voice | 0b6 | no  | no |
| Qwen3-TTS-12Hz-1.7B-VoiceDesign | voice_design | 1b7 | yes | no |
| Qwen3-TTS-12Hz-1.7B-Base | base | 1b7 | no  | yes |
| Qwen3-TTS-12Hz-0.6B-Base | base | 0b6 | no  | yes |

Note: `instruct` parameter is silently disabled for 0.6B CustomVoice models in the wrapper
(detected via `self.model.tts_model_size in "0b6"`).

## Inference Pipeline

### CustomVoice generation

1. Validate language + speaker names
2. Build assistant text: `<|im_start|>assistant\n{text}<|im_end|>\n<|im_start|>assistant\n`
3. Tokenize text → `input_ids`
4. Optionally build instruct text tokens: `<|im_start|>user\n{instruct}<|im_end|>\n`
5. Call `model.generate(input_ids, instruct_ids, languages, speakers, **gen_kwargs)`
6. Decode output codes via `model.speech_tokenizer.decode([{"audio_codes": c} for c in codes])`
7. Return `(wavs, sample_rate)`

### VoiceDesign generation

Same as CustomVoice, but no `speakers` arg. `instruct_ids` controls voice style.

### Voice clone (Base) generation

1. Build or receive pre-built `voice_clone_prompt` (contains `ref_code`, `ref_spk_embedding`, etc.)
2. Tokenize synthesis text and optionally reference text
3. Call `model.generate(input_ids, ref_ids, voice_clone_prompt, languages, **gen_kwargs)`
4. Prepend `ref_code` to generated codes for decode
5. Decode combined codes, then trim the reference portion from the output waveform
6. Return `(wavs, sample_rate)`

## Output Format

- **Type**: `List[np.ndarray]` — one array per batch item
- **Array dtype**: `float32`
- **Shape**: 1-D `(num_samples,)` after trimming
- **Sample rate**: integer returned as second element of the tuple, sourced from
  `model.speech_tokenizer.get_output_sample_rate()`

To save to file: `soundfile.write("output.wav", wavs[0], sr)`
