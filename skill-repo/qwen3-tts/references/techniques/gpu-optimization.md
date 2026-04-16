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

The CLI backend selects dtype **automatically**:
- On a CUDA GPU: `bfloat16` is used, halving VRAM usage with negligible quality loss
- On CPU: `float32` is used (bfloat16 is not available on CPU hardware)

There is no `--dtype` CLI flag — dtype selection is hardcoded in the backend based on the detected device. The official evaluation in the README was conducted with `dtype=torch.bfloat16`.

**Python API (not CLI):** If using the Python API directly, you can control dtype explicitly:

```python
# Python API (not CLI) — dtype control
import torch
from qwen_tts import Qwen3TTSModel

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

The CLI uses flash attention **automatically if `flash-attn` is installed** — there is no `--flash-attn` flag. Install it separately to enable it:

```bash
pip install flash-attn --no-build-isolation
```

If `flash-attn` is not installed, the backend falls back to standard attention automatically. Flash Attention 2 requires a CUDA GPU with compute capability 8.0+ (Ampere or newer). It is not available on CPU or older GPUs.

**Python API (not CLI):** If using the Python API directly, you can specify the attention implementation explicitly:

```python
# Python API (not CLI) — explicit flash attention
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="cuda:0",
    dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
)
```

### CPU Fallback

Running on CPU is supported but impractical for real use:
- Inference on CPU is **very slow** — expect 5-30 minutes per sentence depending on hardware
- CPU inference automatically uses `float32`
- Use CPU only for testing import correctness, not for actual synthesis

```bash
uv run python -m qwen3_tts_cli generate text "Test." \
  --speaker Aiden \
  --device cpu \
  -o test.wav
```

**Python API (not CLI):** Explicit CPU loading:

```python
# Python API (not CLI)
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

**Python API (not CLI):**

```python
# Python API (not CLI) — batch generation
wavs, sr = model.generate_custom_voice(
    text=["Line one.", "Line two.", "Line three."],
    speaker="Aiden",
)
```

Batch size is limited by available VRAM. A batch of 8-16 short sentences typically fits within 8GB VRAM on the 1.7B model.

### device_map="auto"

For multi-GPU setups or when you want HuggingFace Accelerate to distribute layers automatically:

**Python API (not CLI):**

```python
# Python API (not CLI) — multi-GPU distribution
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="auto",
    dtype=torch.bfloat16,
)
```

For single-GPU setups, `device_map="cuda:0"` is preferred for explicit control.

## CLI Commands

Generate on CPU (slow — for testing only):

```bash
uv run python -m qwen3_tts_cli generate text "Test." \
  --speaker Aiden \
  --device cpu \
  -o test.wav
```

On GPU, simply omit `--device` — the backend detects CUDA automatically and uses bfloat16 + flash attention (if installed):

```bash
uv run python -m qwen3_tts_cli generate text "Test sentence." \
  --speaker Aiden \
  -o out.wav
```

## Under the Hood

`from_pretrained` forwards `device_map`, `dtype`, and `attn_implementation` directly to `AutoModel.from_pretrained`. These are standard HuggingFace Transformers model loading kwargs — Qwen3-TTS adds no special handling beyond what Transformers provides.

The CLI backend (`detect_device`) selects CUDA if available, falls back to MPS on Apple Silicon, then CPU. The dtype is derived from the device: bfloat16 on GPU, float32 on CPU.

The speech tokenizer is loaded separately inside the model's `__init__` and placed on the same device as the main model. It is a lighter model but still requires GPU memory.

Generation uses `@torch.no_grad()` (inference wrappers) and `@torch.inference_mode()` (prompt pre-computation), ensuring no gradient computation overhead during synthesis.

## Gotchas

- **No `--dtype` or `--flash-attn` CLI flags exist.** dtype is chosen automatically (bfloat16 on GPU, float32 on CPU) and flash attention is used automatically if installed. These are only configurable via the Python API.
- **bfloat16 is automatic on CUDA.** You do not need to (and cannot) specify it on the CLI.
- **flash-attn is automatic if installed.** Install it with `pip install flash-attn --no-build-isolation` and it activates automatically.
- **Model weights download on first use**: ~3.4GB for 1.7B variants, ~1.2GB for 0.6B variants. Ensure disk space and network before first run.
- **`flash-attn` is not in `pyproject.toml`** — it must be installed separately. It is not required; omitting it falls back to standard attention.
- **The `sox` binary produces a non-fatal warning** at startup if not installed. This does not affect synthesis output.
- **CPU inference is not a viable production option** — it is orders of magnitude slower than GPU inference.
- Output is always 24kHz regardless of model size or dtype — sample rate is a property of the 12Hz tokenizer's vocoder, not the transformer.
- Changing `temperature`, `top_k`, or `top_p` does not affect VRAM usage — only batch size and sequence length do.

## Sources

- https://github.com/QwenLM/Qwen3-TTS
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base

## Learned from Usage

(No usage notes yet.)
