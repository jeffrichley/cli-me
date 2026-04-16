# Extract Vocals (Two-Stem Mode)

## When to Use

You want to isolate vocals from a song (for karaoke, acapella, remixing) or
extract any single stem with its complement.

## Technique

Demucs's `--two-stems` mode runs the full 4-stem separation but only saves
two files: the selected stem and everything else combined as `no_{stem}`.

## CLI Commands

### Extract vocals + accompaniment
```bash
uv run demucs_cli.py separate song.mp3 --two-stems vocals
```
Produces: `vocals.wav` and `no_vocals.wav`

### Extract drums + complement
```bash
uv run demucs_cli.py separate song.mp3 --two-stems drums
```
Produces: `drums.wav` and `no_drums.wav`

## Under the Hood

- `--two-stems` always produces both the selected stem and its complement
  (`no_{stem}`). The complement is the sum of all other stems.
- Valid stem names depend on the model. For 4-stem models: `vocals`, `drums`,
  `bass`, `other`. For 6-stem (`htdemucs_6s`): also `piano`, `guitar`.
- Passing an invalid stem name (e.g., `--two-stems piano` on a 4-stem model)
  will cause a fatal error.

## Sources

- https://github.com/facebookresearch/demucs/blob/main/README.md
- `demucs/separate.py` lines 66-68 — two-stems arg
- `demucs/separate.py` lines 185-218 — stem saving logic

## Learned from Usage

(No entries yet — agents update this section after using the commands.)
