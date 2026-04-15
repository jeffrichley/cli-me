# Fade Transitions (Fade In / Fade Out)

## When to Use

Use fade transitions to open a video from black (fade in) or close to black (fade out). They create a professional, polished feel for intros, outros, and scene transitions. Combine video and audio fades for full effect. Use `color=white` for a bright/clean fade style.

## Technique

**Video fade**: `fade=t=in:st=0:d=1` (type, start time, duration in seconds)
- `t=in` — fade from black to visible
- `t=out` — fade from visible to black
- `st=` — start time in seconds
- `d=` — duration in seconds

**Fade out** requires knowing the video duration to compute the start time:
- `st = total_duration - fade_duration`
- Get duration with `ffprobe -v quiet -show_entries format=duration -of csv=p=0 input.mp4`

**Audio fade**: `afade=t=in:st=0:d=1` — same parameters as video fade.

**White fade**: add `color=white` to the fade filter: `fade=t=in:st=0:d=1:color=white`

Both `fade` and `afade` can be chained in a single `-vf`/`-af` or combined in `-filter_complex`.

## CLI Commands

**Fade in from black (first 1 second):**
```bash
ffmpeg -i input.mp4 \
  -vf "fade=t=in:st=0:d=1" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_fadein.mp4
```

**Fade out to black (last 1 second of a 30-second video):**
```bash
ffmpeg -i input.mp4 \
  -vf "fade=t=out:st=29:d=1" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_fadeout.mp4
```

**Both fade in and fade out + audio fades (30-second video, 1-second each):**
```bash
ffmpeg -i input.mp4 \
  -vf "fade=t=in:st=0:d=1,fade=t=out:st=29:d=1" \
  -af "afade=t=in:st=0:d=1,afade=t=out:st=29:d=1" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  output_full_fades.mp4
```

**White fade in (fade from white instead of black):**
```bash
ffmpeg -i input.mp4 \
  -vf "fade=t=in:st=0:d=1:color=white" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_white_fadein.mp4
```

**Audio-only fade (preserve video, fade audio in/out):**
```bash
ffmpeg -i input.mp4 \
  -c:v copy \
  -af "afade=t=in:st=0:d=1,afade=t=out:st=29:d=1" \
  output_audio_fades.mp4
```
Note: `-c:v copy` only works here because no video filter is applied.

**Auto-compute fade-out start time with shell script:**
```bash
DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 input.mp4)
FADE_DUR=1
FADEOUT_START=$(echo "$DURATION - $FADE_DUR" | bc)

ffmpeg -i input.mp4 \
  -vf "fade=t=in:st=0:d=${FADE_DUR},fade=t=out:st=${FADEOUT_START}:d=${FADE_DUR}" \
  -af "afade=t=in:st=0:d=${FADE_DUR},afade=t=out:st=${FADEOUT_START}:d=${FADE_DUR}" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  output_auto_fades.mp4
```

## Under the Hood

The `fade` video filter linearly blends each frame with a solid color (default black) over the specified duration. At `t=in`, frame 0 starts at 100% color and blends to 0% color at frame `d*fps`. At `t=out`, it starts at 0% color at `st*fps` and reaches 100% color at `(st+d)*fps`.

`afade` applies a linear gain ramp to audio samples within the time window. `t=in` ramps gain from 0 to 1; `t=out` ramps from 1 to 0. Like the video fade, no resampling occurs — it's a pure gain operation.

Both `fade` and `afade` can appear multiple times in the same filter chain (comma-separated in `-vf`/`-af`). FFmpeg processes them sequentially — fade-in first, then fade-out — which is the correct order since they operate on non-overlapping time ranges.

`color=white` in the `fade` filter sets the target blend color. Any valid FFmpeg color string works: `black` (default), `white`, `red`, hex like `#FF0000`.

When using `-c:v copy` with audio fades only: since no video filter is applied, FFmpeg remuxes the video stream as-is (no re-encode). Audio is decoded and re-encoded with the fade applied. This is the most efficient path when only the audio needs modification.

## Sources

- DEV Community: https://dev.to/dak425/add-fade-in-and-fade-out-effects-with-ffmpeg-2bj7
- Editframe — Crossfade and fade effects: https://www.editframe.com/guides/crossfade-between-two-videos-using-ffmpeg
- Editframe: https://www.editframe.com/guides/ffmpeg-fade-filter

## Learned from Usage

- `ffprobe` returns duration as a float (e.g., `30.033`). When computing `st` for fade-out, subtract slightly more than `d` to ensure the fade completes before the last frame.
- Chaining two fade filters on the same stream (in + out) is only reliable when their time ranges don't overlap. A 1-second fade on a 2-second video would overlap — reduce `d` accordingly.
- `afade` with `t=out` on streams with unknown duration: use `st=0:d=1:curve=exp` and combine with `-t` to trim — avoids needing to know exact duration.
- For cross-dissolve (fade between two clips), use `xfade` filter instead — it handles the blend of two input streams simultaneously.
- `color=` accepts color names, hex `#RRGGBB`, or hex with alpha `#RRGGBBAA`.
