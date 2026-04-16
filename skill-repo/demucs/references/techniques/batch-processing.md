# Batch Processing

## When to Use

You have multiple audio files to separate and want to process them
efficiently in sequence or with controlled parallelism.

## Technique

Demucs natively accepts multiple file arguments. Each file is processed
sequentially through the same loaded model, avoiding repeated model loading
overhead. The CLI wrapper passes all files in a single invocation.

## CLI Commands

### Multiple files in one call
```bash
uv run demucs_cli.py separate song1.mp3 song2.wav song3.flac
```

### All MP3s in a directory (shell glob — bash/zsh only)
```bash
uv run demucs_cli.py separate /path/to/music/*.mp3
```
**Note:** Shell globs (`*.mp3`) are expanded by the shell, not the CLI.
On Windows CMD/PowerShell, globs are not expanded — list files explicitly
or use bash (Git Bash, WSL).

### Custom output directory
```bash
uv run demucs_cli.py separate *.mp3 --output ./stems
```

### Batch with quality settings
```bash
uv run demucs_cli.py separate *.mp3 --model htdemucs_ft --shifts 3 --format flac
```

## Under the Hood

- The model loads once and processes each file sequentially
- Output structure: `{output}/{model_name}/{track_name}/{stem}.{ext}`
- Each track gets its own subdirectory to avoid filename collisions
- Demucs does not natively skip already-processed files; the agent should
  check for existing output before re-processing
- For CPU processing, `--jobs` enables multi-threaded chunk processing
  per file but does NOT parallelize across files
- The CLI enforces a 1-hour timeout. Large batches of long files may need
  to be split into smaller groups.
- Demucs silently overwrites existing output files on re-run. Check for
  existing output before re-processing if you need to preserve prior results.

## Sources

- https://github.com/facebookresearch/demucs/blob/main/README.md
- `demucs/separate.py` lines 153-218 — per-track loop

## Learned from Usage

(No entries yet — agents update this section after using the commands.)
