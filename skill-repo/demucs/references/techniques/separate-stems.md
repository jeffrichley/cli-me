# Separate Audio into Stems

## When to Use

You have an audio file (song, podcast, recording) and want to split it into
individual stems: vocals, drums, bass, and other instruments.

## Technique

Demucs uses a Hybrid Transformer neural network to predict each stem's
waveform from the mixed audio. The default model (`htdemucs`) produces 4
stems. Processing happens in chunks to manage memory, with overlapping
segments blended via crossfade.

## CLI Commands

### Full 4-stem separation (default)
```bash
uv run demucs_cli.py separate song.mp3
```

### Specify output directory
```bash
uv run demucs_cli.py separate song.mp3 --output ./my-stems
```

### Use a specific model
```bash
uv run demucs_cli.py separate song.mp3 --model htdemucs_ft
```

### Higher quality with shifts
```bash
uv run demucs_cli.py separate song.mp3 --shifts 5
```

### Force CPU processing
```bash
uv run demucs_cli.py separate song.mp3 --device cpu
```

### Reduce VRAM usage
```bash
uv run demucs_cli.py separate song.mp3 --segment 7
```

### Multiple files
```bash
uv run demucs_cli.py separate song1.mp3 song2.wav song3.flac
```

## Under the Hood

- Demucs auto-detects CUDA GPUs and uses them by default
- The `--shifts` parameter applies random time offsets and averages predictions,
  improving SDR by ~0.2 dB per shift at the cost of processing time
- `--segment` controls chunk size in seconds (integer only); smaller = less VRAM
  but more boundary artifacts. Max for htdemucs is 7 seconds.
- `--overlap` (default 0.25) controls crossfade between chunks
- Output is 16-bit WAV by default; use `--format` to change

## Sources

- https://github.com/facebookresearch/demucs/blob/main/README.md
- `demucs/separate.py` — CLI implementation
- `demucs/api.py` — Separator class
- `demucs/apply.py` — apply_model() with shift/chunk logic

## Learned from Usage

(No entries yet — agents update this section after using the commands.)
