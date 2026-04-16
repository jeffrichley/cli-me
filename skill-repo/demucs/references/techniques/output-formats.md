# Output Formats

## When to Use

You need stems in a specific audio format or bit depth for your workflow
(mixing, mastering, streaming, archival).

## Technique

Demucs defaults to 16-bit integer WAV. You can switch to 24-bit WAV,
32-bit float WAV, MP3, or FLAC. MP3 encoding uses lameenc with
configurable bitrate and quality preset.

## CLI Commands

### Default (16-bit WAV)
```bash
uv run demucs_cli.py separate song.mp3
```

### 24-bit WAV (pro audio)
```bash
uv run demucs_cli.py separate song.mp3 --int24
```

### 32-bit float WAV (maximum precision)
```bash
uv run demucs_cli.py separate song.mp3 --float32
```

### MP3 output
```bash
uv run demucs_cli.py separate song.mp3 --format mp3
```

### MP3 with custom bitrate
```bash
uv run demucs_cli.py separate song.mp3 --format mp3 --mp3-bitrate 192
```

### FLAC output (lossless compression)
```bash
uv run demucs_cli.py separate song.mp3 --format flac
```

## Under the Hood

- WAV is the native output; MP3/FLAC require post-conversion
- `--int24` and `--float32` are mutually exclusive. If both are passed, `--int24`
  takes precedence silently. These only affect WAV output.
- `--mp3-bitrate` and `--mp3-preset` are only applied when `--format mp3` is used.
  They are silently ignored for WAV/FLAC output.
- `--clip-mode rescale` (default) scales the entire signal if any sample
  exceeds ±1.0. `clamp` hard-clips at ±1.0.
- MP3 preset ranges from 2 (highest quality, slowest) to 7 (fastest, lower quality)
- FLAC preserves full quality with ~50% size reduction vs WAV
- The model's native sample rate is 44100 Hz for all current models
- Default output directory is `separated/` when `--output` is not specified

## Sources

- https://github.com/facebookresearch/demucs/blob/main/README.md
- `demucs/audio.py` lines 236-265 — save_audio implementation
- `demucs/separate.py` lines 73-92 — format CLI flags

## Learned from Usage

- On Windows, WAV/FLAC output requires ffmpeg shared DLLs (avcodec-*.dll etc.)
  next to ffmpeg.exe. The "essentials" build lacks these. MP3 always works
  (uses lameenc, bypasses torchaudio). See gotchas.md for setup details.
- `--int24` and `--float32` may silently produce 16-bit WAV on some Windows
  torchaudio backends. Verify with ffprobe if bit depth matters.
  (2026-04-16)
