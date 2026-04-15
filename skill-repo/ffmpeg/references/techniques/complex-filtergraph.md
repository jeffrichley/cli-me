# Complex Filtergraph

## When to Use

Use `-filter_complex` whenever you have more than one input, need to route streams to multiple outputs, or need to combine filters that produce or consume named stream labels. `-vf` and `-af` only work on single-input, single-output chains — they cannot handle multi-input operations like overlays, stacks, or grids.

Common use cases: picture-in-picture (PiP), side-by-side comparison, video grids, logo overlays, and merging multi-channel audio.

## Technique

**`-filter_complex` is required for all multi-input filter operations.** Using `-vf` with multiple inputs is an error.

**Every label produced in the filtergraph must be consumed.** Either map it with `-map [label]` or connect it as input to another filter. Unconsumed labels cause an error: `Output pad ... not connected`.

**PiP overlay:** `overlay=X:Y` places the second input on top of the first. Coordinates are relative to the top-left of the base video. Use `main_w`, `main_h`, `overlay_w`, `overlay_h` as symbolic dimensions for resolution-independent placement.

**`hstack`/`vstack`:** Require inputs with identical height (hstack) or width (vstack). If dimensions do not match, scale first.

**`xstack`:** For arbitrary grids. Uses `layout=` to specify absolute pixel positions for each input. More flexible than nested hstack/vstack but syntax is verbose.

**Audio: `amerge` vs `amix`:**
- `amerge` combines channels from multiple mono/stereo inputs into a single multi-channel stream (e.g., two stereo streams into one 4-channel stream). Use with `pan` filter to downmix if needed.
- `amix` mixes multiple audio streams together into one stream at the same channel count, summing them. Reduces volume by default unless `normalize=0` is passed.

**Logo overlay:** Same as PiP — use `overlay`. Load the logo as a separate input, scale it if needed, then overlay at a fixed position. If the logo has an alpha channel (PNG), FFmpeg handles compositing automatically.

## CLI Commands

**PiP — small video in bottom-right corner:**
```bash
ffmpeg -i main.mp4 -i overlay.mp4 \
  -filter_complex \
    "[1:v]scale=320:-1[pip];
     [0:v][pip]overlay=main_w-overlay_w-20:main_h-overlay_h-20[v]" \
  -map "[v]" -map 0:a \
  -c:v libx264 -crf 18 -c:a copy \
  output.mp4
```

**PiP — small video in top-right corner:**
```bash
ffmpeg -i main.mp4 -i overlay.mp4 \
  -filter_complex \
    "[1:v]scale=320:-1[pip];
     [0:v][pip]overlay=main_w-overlay_w-20:20[v]" \
  -map "[v]" -map 0:a \
  -c:v libx264 -crf 18 -c:a copy \
  output.mp4
```

**Side-by-side (hstack) — same height inputs:**
```bash
ffmpeg -i left.mp4 -i right.mp4 \
  -filter_complex "[0:v][1:v]hstack=inputs=2[v]" \
  -map "[v]" -map 0:a \
  -c:v libx264 -crf 18 -c:a copy \
  output.mp4
```

**Side-by-side (hstack) — different heights (scale right to match left):**
```bash
ffmpeg -i left.mp4 -i right.mp4 \
  -filter_complex \
    "[1:v]scale=-1:ih[right_scaled];
     [0:v][right_scaled]hstack=inputs=2[v]" \
  -map "[v]" -map 0:a \
  -c:v libx264 -crf 18 -c:a copy \
  output.mp4
```

Note: `ih` in the scale filter refers to the input height of that specific filter's input — here it matches the height of `right.mp4` itself, not `left.mp4`. To match left's height, use a fixed value or `[0:v]`'s height via a `split`+`scale` combination.

Safer approach when heights differ — scale both to a fixed height:
```bash
ffmpeg -i left.mp4 -i right.mp4 \
  -filter_complex \
    "[0:v]scale=-1:720[l];
     [1:v]scale=-1:720[r];
     [l][r]hstack=inputs=2[v]" \
  -map "[v]" -map 0:a \
  -c:v libx264 -crf 18 -c:a copy \
  output.mp4
```

**2x2 grid with xstack:**
```bash
ffmpeg -i a.mp4 -i b.mp4 -i c.mp4 -i d.mp4 \
  -filter_complex \
    "[0:v]scale=640:360[v0];
     [1:v]scale=640:360[v1];
     [2:v]scale=640:360[v2];
     [3:v]scale=640:360[v3];
     [v0][v1][v2][v3]xstack=inputs=4:layout=0_0|640_0|0_360|640_360[v]" \
  -map "[v]" \
  -c:v libx264 -crf 18 \
  output.mp4
```

**2x2 grid with hstack + vstack (alternative approach):**
```bash
ffmpeg -i a.mp4 -i b.mp4 -i c.mp4 -i d.mp4 \
  -filter_complex \
    "[0:v][1:v]hstack[top];
     [2:v][3:v]hstack[bottom];
     [top][bottom]vstack[v]" \
  -map "[v]" \
  -c:v libx264 -crf 18 \
  output.mp4
```

**Side-by-side with merged audio (amerge):**
```bash
ffmpeg -i left.mp4 -i right.mp4 \
  -filter_complex \
    "[0:v][1:v]hstack=inputs=2[v];
     [0:a][1:a]amerge=inputs=2[a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -crf 18 -c:a aac -ac 2 \
  output.mp4
```

The `-ac 2` downmixes the merged 4-channel stream back to stereo for delivery.

**Logo overlay (PNG with transparency):**
```bash
ffmpeg -i video.mp4 -i logo.png \
  -filter_complex \
    "[1:v]scale=150:-1[logo];
     [0:v][logo]overlay=main_w-overlay_w-20:20[v]" \
  -map "[v]" -map 0:a \
  -c:v libx264 -crf 18 -c:a copy \
  output.mp4
```

## Under the Hood

`-filter_complex` builds a directed acyclic graph (DAG) of filters. Each filter node has named input pads and output pads. Unnamed pads use auto-generated labels. Named labels (e.g., `[v]`, `[pip]`) are wires connecting filter outputs to filter inputs or to `-map` directives.

`overlay` is a two-input filter: the first input is the base (background), the second is the overlay (foreground). Coordinate expressions are evaluated by libavfilter's expression evaluator and have access to `main_w`, `main_h` (dimensions of the first input) and `overlay_w`, `overlay_h` (dimensions of the second input) at filter initialization time.

`hstack` and `vstack` are optimized for exactly two inputs by default; use `inputs=N` for more. They require matching perpendicular dimensions and will error otherwise.

`xstack` with `layout=` takes `x_y` pairs separated by `|`, one per input, defining the top-left corner of each tile in the output canvas. The output canvas size is automatically computed to fit all tiles.

`amerge` increases the channel count by appending channels from each input. `amix` sums samples from each input, scaling by `1/N` by default to prevent clipping (disable with `normalize=0`).

## Sources

- FFmpeg — "Filters Documentation" (overlay, hstack, vstack, xstack, amerge, amix reference): https://ffmpeg.org/ffmpeg-filters.html
- FFmpeg Wiki — "Filtering Guide": https://trac.ffmpeg.org/wiki/FilteringGuide
- OTTVerse — "Stack Videos Horizontally, Vertically, in a Grid With FFmpeg": https://ottverse.com/stack-videos-horizontally-vertically-grid-with-ffmpeg/
- ffmpeg-api.com — "Create Picture-in-Picture Videos with FFmpeg": https://ffmpeg-api.com/learn/ffmpeg/recipe/picture-in-picture

## Learned from Usage

- The most common filtergraph error is an unconsumed label — every `[label]` on the right side of a filter definition must appear either as input to another filter or in a `-map` flag.
- `overlay` coordinate expressions are computed once at start, not per-frame. For animated overlays, use the `overlay` filter with `x=` and `y=` as dynamic expressions using `t` for time.
- When using `xstack` for a grid, inputs with slightly different durations will cause the grid to freeze when the shortest stream ends. Add `-shortest` or pad shorter streams with `tpad`.
- `amerge` followed by `-ac 2` is cleaner than `amix` for side-by-side videos where you want both audio tracks present and equal — `amix` will halve each track's volume.
