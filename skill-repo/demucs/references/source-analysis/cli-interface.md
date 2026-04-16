# CLI Interface

## Invocation

```bash
demucs [OPTIONS] TRACK [TRACK ...]
python -m demucs [OPTIONS] TRACK [TRACK ...]
```

## Complete Flag Reference

### Positional Arguments
| Argument | Description |
|----------|-------------|
| `tracks` | One or more audio file paths |

### Model Selection (mutually exclusive)
| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--name` | `-n` | `htdemucs` | Pretrained model name |
| `--sig` | `-s` | — | Locally trained XP signature |
| `--repo` | — | — | Path to folder with custom models |

### Output Control
| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--out` | `-o` | `separated` | Output directory |
| `--filename` | — | `{track}/{stem}.{ext}` | Output filename template. Variables: `{track}`, `{trackext}`, `{stem}`, `{ext}` |
| `--list-models` | — | — | List available models and exit |
| `--verbose` | `-v` | — | Verbose output |

### Device & Processing
| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--device` | `-d` | Auto (cuda if available, else cpu) | Compute device |
| `--jobs` | `-j` | `0` | Parallel workers (CPU only) |
| `--shifts` | — | `1` | Random shift augmentations for quality (0-10) |
| `--overlap` | — | `0.25` | Overlap between chunks (0.0-1.0) |

### Chunking (mutually exclusive)
| Flag | Default | Description |
|------|---------|-------------|
| `--no-split` | — | Disable chunking (uses more memory) |
| `--segment` | Model default | Chunk length in seconds |

### Stem Selection
| Flag | Default | Description |
|------|---------|-------------|
| `--two-stems` | — | Extract one stem + complement (e.g., `vocals`) |

**Note:** `--other-method` exists in the unreleased source but is NOT in PyPI 4.0.1.

### Audio Format (mutually exclusive)
| Flag | Default | Description |
|------|---------|-------------|
| (none) | ✓ | 16-bit integer WAV |
| `--int24` | — | 24-bit integer WAV |
| `--float32` | — | 32-bit float WAV |
| `--mp3` | — | MP3 output |
| `--flac` | — | FLAC output |

### MP3 Options
| Flag | Default | Description |
|------|---------|-------------|
| `--mp3-bitrate` | `320` | Bitrate in kbps |
| `--mp3-preset` | `2` | Encoder quality (2=best, 7=fastest) |

### Clipping
| Flag | Default | Description |
|------|---------|-------------|
| `--clip-mode` | `rescale` | Clipping strategy: `rescale`, `clamp` |

## Output Directory Structure

```
{out}/{model_name}/{track_name}/{stem}.{ext}
```

Example:
```
separated/htdemucs/song/
├── bass.wav
├── drums.wav
├── other.wav
└── vocals.wav
```
