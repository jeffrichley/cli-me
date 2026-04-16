# pyannote Gotchas

Known issues, workarounds, and things that will bite you.

## HuggingFace Token Required

Most pyannote models are gated. You must:
1. Create a HuggingFace account
2. Visit the model page and accept the terms
3. Set `HF_TOKEN` environment variable or pass `--token`

Without this, `Pipeline.from_pretrained()` will fail with a 401 error.

## First Run Downloads ~500MB

The first time you load a pipeline, it downloads model weights from HuggingFace.
This takes 1-5 minutes depending on connection speed. Subsequent runs use the
cache at `~/.cache/huggingface/hub/`.

To pre-download: `pyannote-audio download pyannote/speaker-diarization-community-1`

## pyannote-audio.exe Is NOT on PATH

On this system, the binary is at:
`C:/Users/jeffr/AppData/Roaming/Python/Python313/Scripts/pyannote-audio.exe`

Our CLI wrapper uses the Python API directly, so this doesn't matter for us.

## GPU Memory

- Segmentation model: ~1GB VRAM
- Embedding model: ~0.5GB VRAM
- Full diarization pipeline: ~2GB VRAM
- Falls back to CPU automatically if CUDA/MPS unavailable

## Processing Time

- ~10x realtime on CPU (1 hour audio takes ~6 minutes)
- ~50x realtime on GPU
- Long files process in sliding windows — memory-efficient but slower

## No Interactive Prompts

pyannote.audio does not have interactive prompts that would hang agents.
No `-y` or `--force` flags needed — it's purely non-interactive by design.

## Thread Safety

The pipeline object is NOT thread-safe. For parallel processing, use
multiprocessing (one pipeline per process) instead of threading.
