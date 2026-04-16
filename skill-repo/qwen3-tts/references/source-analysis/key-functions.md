---
title: Key Functions and Generation Parameters
tags: [source-analysis, qwen3-tts]
sources: [https://github.com/QwenLM/Qwen3-TTS]
created: 2026-04-16
updated: 2026-04-16
---

# Key Functions and Generation Parameters

## Generation Kwargs

All three `generate_*` methods accept `**kwargs` which are merged with defaults from the
model checkpoint's `generate_config.json`. The merge rule is:

1. Explicit user value (not `None`) → use it
2. Value in `generate_config.json` → use it
3. Hard-coded default in `_merge_generate_kwargs` → use it

### Full Parameter Reference

Documented in `_merge_generate_kwargs` in `qwen3_tts_model.py`:

| Parameter | Type | Hard Default | Description |
|---|---|---|---|
| `do_sample` | `bool` | `True` | Enable sampling; recommended `True` for all uses |
| `top_k` | `int` | `50` | Top-k sampling; filters to top-k token candidates |
| `top_p` | `float` | `1.0` | Top-p (nucleus) sampling threshold |
| `temperature` | `float` | `0.9` | Sampling temperature; higher = more random |
| `repetition_penalty` | `float` | `1.05` | Penalizes repeated tokens/codes |
| `subtalker_dosample` | `bool` | `True` | Sampling switch for sub-talker (12Hz tokenizer only) |
| `subtalker_top_k` | `int` | `50` | Top-k for sub-talker sampling (12Hz tokenizer only) |
| `subtalker_top_p` | `float` | `1.0` | Top-p for sub-talker sampling (12Hz tokenizer only) |
| `subtalker_temperature` | `float` | `0.9` | Temperature for sub-talker sampling (12Hz tokenizer only) |
| `max_new_tokens` | `int` | `2048` | Maximum number of new codec tokens to generate |

**Note on sub-talker params**: Sub-talker parameters are only valid for the 12Hz tokenizer
(`qwen3-tts-tokenizer-v2`). They control a secondary generation stage in the Dual-Track
architecture. Pass them to all models using 12Hz weights — these are all models in the
current release.

### Additional kwargs

Any HuggingFace Transformers `generate()` kwargs can also be passed via `**kwargs`; they
are forwarded directly to `Qwen3TTSForConditionalGeneration.generate(...)`.

## Model-Level generate() Signature

The underlying `model.generate()` (called inside the wrapper) accepts:

```python
model.generate(
    input_ids,                # List[torch.Tensor] — tokenized synthesis text
    ref_ids=None,             # List[Optional[torch.Tensor]] — tokenized reference text (base model)
    voice_clone_prompt=None,  # dict with ref_code, ref_spk_embedding, etc. (base model)
    instruct_ids=None,        # List[Optional[torch.Tensor]] — tokenized instruct text
    languages=None,           # List[str]
    speakers=None,            # List[str] (custom_voice model only)
    non_streaming_mode=True,  # bool
    **gen_kwargs,             # do_sample, top_k, top_p, temperature, etc.
)
```

Returns: `(talker_codes_list, _)` where `talker_codes_list` is `List[torch.Tensor]` of codec codes.

## Speech Tokenizer Key Methods

```python
# Qwen3TTSTokenizer
tokenizer.encode(audio, sr=None)           # → ModelOutput with audio_codes
tokenizer.decode(encoded)                  # → (List[np.ndarray], int)
tokenizer.get_output_sample_rate()         # → int
tokenizer.get_input_sample_rate()          # → int
tokenizer.get_encode_downsample_rate()     # → int
tokenizer.get_decode_upsample_rate()       # → int
```

Standalone tokenizer load:
```python
from qwen_tts import Qwen3TTSTokenizer
tokenizer = Qwen3TTSTokenizer.from_pretrained(
    "Qwen/Qwen3-TTS-Tokenizer-12Hz",
    device_map="cuda:0",
)
```

## Fine-tuning Entry Points

Fine-tuning uses two scripts in `finetuning/`:

### `prepare_data.py`

```bash
python prepare_data.py \
  --device cuda:0 \
  --tokenizer_model_path Qwen/Qwen3-TTS-Tokenizer-12Hz \
  --input_jsonl train_raw.jsonl \
  --output_jsonl train_with_codes.jsonl
```

Input JSONL fields: `audio` (wav path), `text` (transcript), `ref_audio` (reference speaker wav).

### `sft_12hz.py`

```bash
python sft_12hz.py \
  --init_model_path Qwen/Qwen3-TTS-12Hz-1.7B-Base \
  --output_model_path output \
  --train_jsonl train_with_codes.jsonl \
  --batch_size 32 \
  --lr 2e-6 \
  --num_epochs 10 \
  --speaker_name speaker_test
```

Fine-tuned checkpoints are saved as `output/checkpoint-epoch-{N}/` in HuggingFace
format and can be loaded directly with `Qwen3TTSModel.from_pretrained(...)`.

Only single-speaker fine-tuning is supported in this release. The tuned model uses
`generate_custom_voice` for inference (the speaker name becomes the `--speaker_name`
arg used during training).

## Evaluation Defaults

From the README evaluation section: models were evaluated with `dtype=torch.bfloat16`,
`max_new_tokens=2048`, all other sampling params from `generate_config.json`.
`language="auto"` was used for some test sets; explicit language strings for others.

## Audio Input Normalization

The wrapper's `_normalize_audio_inputs` method supports:

| Input form | Behavior |
|---|---|
| `str` (local path) | Loaded via `librosa.load(path, sr=None, mono=True)` |
| `str` (URL starting with `http://` or `https://`) | Downloaded via `urllib.request`, read via `soundfile` |
| `str` (base64, starting with `data:audio` or length > 256 with no path separators) | Decoded from base64, read via `soundfile` |
| `(np.ndarray, int)` tuple | Used directly; array cast to `float32` |
| `np.ndarray` alone | Raises `ValueError` — must wrap in tuple with sr |

Multi-channel audio is converted to mono by averaging channels.
