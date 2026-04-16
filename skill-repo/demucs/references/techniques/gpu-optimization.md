# GPU / CUDA Optimization

## When to Use

You want to maximize processing speed or work around GPU memory limitations
when separating audio with Demucs.

## Technique

Demucs auto-detects CUDA GPUs via `torch.cuda.is_available()`. GPU processing
is ~5x faster than CPU. For memory-constrained GPUs, reduce segment size.
For maximum quality, increase shifts (at the cost of proportional slowdown).

## CLI Commands

### Auto-detect device (default behavior)
```bash
uv run demucs_cli.py separate song.mp3
# Uses CUDA if available, then MPS (Apple Silicon), otherwise CPU
```

### Force specific device
```bash
uv run demucs_cli.py separate song.mp3 --device cuda
uv run demucs_cli.py separate song.mp3 --device cuda:1
uv run demucs_cli.py separate song.mp3 --device cpu
```

### Reduce VRAM usage (low-memory GPU)
```bash
uv run demucs_cli.py separate song.mp3 --segment 7
```

### Disable chunking (high-memory GPU, faster)
```bash
uv run demucs_cli.py separate song.mp3 --no-split
```

### CPU with parallel workers
```bash
uv run demucs_cli.py separate song.mp3 --device cpu --jobs 4
```

### Quality vs speed tradeoff
```bash
# Fast (default): 1 shift
uv run demucs_cli.py separate song.mp3 --shifts 1

# High quality: 5 shifts (~5x slower)
uv run demucs_cli.py separate song.mp3 --shifts 5

# Maximum quality: 10 shifts (~10x slower)
uv run demucs_cli.py separate song.mp3 --shifts 10
```

## Under the Hood

- **VRAM requirements**: ~4-7 GB for default settings. `--segment 7` drops to ~2 GB.
- **Multi-worker threading** (`--jobs`) only works on CPU. On GPU, the GPU itself
  handles parallelism.
- **`--no-split`** processes the entire track as one chunk. Fastest but requires
  enough VRAM to hold the full track. Useful for short clips on beefy GPUs.
- **Shifts** apply random time offsets and average all predictions. Each shift
  adds one full inference pass. SDR improves ~0.2 dB per shift.
- **Environment variable** `PYTORCH_NO_CUDA_MEMORY_CACHING=1` reduces peak VRAM
  at the cost of speed (disables PyTorch's memory allocator cache).
- **Apple Silicon (MPS)**: Auto-detected via `torch.backends.mps.is_available()`.
  Use `--device mps` to force it. Performance is between CPU and CUDA.
- **Multi-GPU**: Demucs uses a single GPU. Use `CUDA_VISIBLE_DEVICES=1` to
  select which GPU (e.g., pick the one with more VRAM).

## Sources

- https://github.com/facebookresearch/demucs/blob/main/README.md
- https://github.com/facebookresearch/demucs/blob/main/docs/windows.md
- `demucs/api.py` line 58 — device auto-detection
- `demucs/apply.py` lines 174-184 — device handling and worker pool
- `demucs/apply.py` lines 237-256 — shift implementation

## Learned from Usage

(No entries yet — agents update this section after using the commands.)
