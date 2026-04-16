---
title: GPU Optimization and Hardware Requirements
tags: [technique, qwen3-tts, gpu, performance, optimization]
sources: [https://github.com/QwenLM/Qwen3-TTS, https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base]
created: 2026-04-16
updated: 2026-04-16
---

# GPU Optimization and Hardware Requirements

## When to Use

- Setting up Qwen3-TTS on a new machine and choosing which model variant to run
- Optimizing throughput for batch generation workloads
- Debugging out-of-memory errors
- Understanding performance tradeoffs between model sizes

## Technique

### VRAM Requirements

| Model Variant         | Size | VRAM (bfloat16) | VRAM (float32) |
|-----------------------|------|-----------------|----------------|
| 1.7B CustomVoice      | 1.7B | ~4.5GB          | ~9GB           |
| 1.7B VoiceDesign      | 1.7B | ~4.5GB          | ~9GB           |
| 1.7B Base             | 1.7B | ~4.5GB          | ~9GB           |
| 0.6B CustomVoice      | 0.6B | ~1.5GB          | ~3GB           |
| 0.6B Base             | 0.6B | ~1.5GB          | ~3GB           |

These are inference-only figures. Fine-tuning requires 2-3x more VRAM (see fine-tuning page).

The speech tokenizer (12Hz vocoder) adds approximately 500MB on top of the main model's VRAM usage.

### dtype: bfloat16 vs float32

**Always use `dtype=torch.bfloat16`** unless your GPU does not support it (pre-Ampere NVIDIA GPUs, or non-CUDA hardware).

- `bfloat16` halves VRAM usage vs `float32` with negligible quality loss
- The official evaluation in the README was conducted with `dtype=torch.bfloat16`
- `float32` is the fallback for hardware that lacks bfloat16 support

```python
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)
```

### Flash Attention 2

Flash Attention 2 (`flash-attn` package) is optional but recommended for:
- Faster attention computation on long sequences
- Reduced VRAM during attention calculation

Enable it:
```python
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="cuda:0",
    dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
)
```

Flash Attention 2 requires a CUDA GPU with compute capability 8.0+ (Ampere or newer). It is not available on CPU or older GPUs. If `flash-attn` is not installed, omit `attn_implementation` entirely — the default attention implementation will be used.

### CPU Fallback

Running on CPU is supported but impractical for real use:
- Inference on CPU is **very slow** — expect 5-30 minutes per sentence depending on hardware
- CPU inference defaults to `float32` unless explicitly set
- Use CPU only for testing import correctness, not for actual synthesis

To run on CPU:
```python
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    device_map="cpu",
    dtype=torch.float32,
)
```

### Batch Generation for Throughput

Batching multiple texts in a single `generate_*` call is more efficient than sequential calls:

- GPU memory for activations is allocated once per batch
- The transformer processes all items in a batch simultaneously
- Audio decoding (tokenizer) also handles batches natively

Pass a list of strings instead of a single string:

```python
wavs, sr = model.generate_custom_voice(
    text=["Line one.", "Line two.", "Line three."],
    speaker="Aiden",
)
```

Batch size is limited by available VRAM. A batch of 8-16 short sentences typically fits within 8GB VRAM on the 1.7B model.

### device_map="auto"

For multi-GPU setups or when you want HuggingFace Accelerate to distribute layers automatically:

```python
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="auto",
    dtype=torch.bfloat16,
)
```

For single-GPU setups, `device_map="cuda:0"` is preferred for explicit control.

## CLI Commands

Generate with optimized settings (bfloat16 + flash attention):

```bash
python qwen3_tts_cli.py generate text "Test sentence." \
  --speaker Aiden \
  --dtype bfloat16 \
  --flash-attn \
  -o out.wav
```

Generate on CPU (slow — for testing only):

```bash
python qwen3_tts_cli.py generate text "Test." \
  --speaker Aiden \
  --device cpu \
  -o test.wav
```

## Under the Hood

`from_pretrained` forwards `device_map`, `dtype`, and `attn_implementation` directly to `AutoModel.from_pretrained`. These are standard HuggingFace Transformers model loading kwargs — Qwen3-TTS adds no special handling beyond what Transformers provides.

The speech tokenizer is loaded separately inside the model's `__init__` and placed on the same device as the main model. It is a lighter model but still requires GPU memory.

Generation uses `@torch.no_grad()` (inference wrappers) and `@torch.inference_mode()` (prompt pre-computation), ensuring no gradient computation overhead during synthesis.

## Gotchas

- **Model weights download on first use**: ~3.4GB for 1.7B variants, ~1.2GB for 0.6B variants. Ensure disk space and network before first run.
- **`flash-attn` is not in `pyproject.toml`** — it must be installed separately: `pip install flash-attn --no-build-isolation`. It is not required; omitting it falls back to standard attention.
- **The `sox` binary produces a non-fatal warning** at startup if not installed. This does not affect synthesis output.
- **CPU inference is not a viable production option** — it is orders of magnitude slower than GPU inference.
- **`device_map="auto"` with a single GPU** behaves identically to `device_map="cuda:0"` but adds Accelerate overhead. Use explicit device strings when possible.
- Output is always 24kHz regardless of model size or dtype — sample rate is a property of the 12Hz tokenizer's vocoder, not the transformer.
- Changing `temperature`, `top_k`, or `top_p` does not affect VRAM usage — only batch size and sequence length do.

## Sources

- https://github.com/QwenLM/Qwen3-TTS
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base

## Learned from Usage

(No usage notes yet.)
