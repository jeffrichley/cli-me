# Sprite Sheet

## When to Use

Use when you need a grid of video thumbnails in a single image file — for seek-bar previews (video player hover thumbnails), video review contact sheets, editorial storyboards, or scene-change summaries. A sprite sheet is more efficient than individual frame images when the consumer needs to display many previews quickly (e.g., a video player showing thumbnails as the user scrubs the timeline).

## Technique

**`tile=COLSxROWS` filter:** The core of sprite sheet creation. Buffers frames and lays them out in a grid. `tile=10x10` produces a 100-cell grid. The output is one image per completed tile.

**Sampling interval computation:**
To get a specific number of frames covering the full video:
```
INTERVAL = DURATION / (COLS * ROWS)
fps = 1/INTERVAL
```
Example: 60-second video, 10x6 grid (60 cells) → `1/1` = 1fps. 600-second video, 10x6 grid → `1/10` = one frame every 10 seconds.

**`-frames:v 1` for single output:**
Without this, tile produces one output image per completed tile. With a 10x10 grid and 1000 frames, you'd get 10 files. Add `-frames:v 1` to force exactly one output image (the first completed tile).

**Scale for seek bars vs review:**
- Seek bar thumbnails (video player hover): `scale=160:90` — small, fast to load, standard 16:9 at 160px
- Editorial review contact sheet: `scale=320:180` — large enough to read content
- Use `scale=160:-1` to maintain aspect ratio at 160px wide for non-16:9 content

**Padding and margin:**
- `tile=10x10:padding=2` — 2px padding between cells
- `tile=10x10:margin=4` — 4px outer margin around the grid
- `tile=10x10:padding=2:margin=4:color=black` — padding + margin with black background

**Scene-change grid:**
`select='gt(scene,0.4)'` selects frames where the scene score exceeds 0.4 (0–1 scale, higher = more scene change). Combined with `tile`, this produces a "highlights" grid showing only visually distinct moments. Threshold 0.4 is a practical default — lower it (0.3) for more frames, raise it (0.6) for only major cuts.

## CLI Commands

**Basic contact sheet (10x10 grid, one frame per second):**
```bash
ffmpeg -i input.mp4 -vf "fps=1,scale=160:90,tile=10x10" -frames:v 1 contact_sheet.jpg
```

**Seek-bar sprite with computed interval (60-cell grid for 600s video):**
```bash
# DURATION=600, COLS=10, ROWS=6 → INTERVAL=10
ffmpeg -i input.mp4 -vf "fps=1/10,scale=160:90,tile=10x6" -frames:v 1 seekbar.jpg
```

**Seek-bar sprite with shell-computed interval:**
```bash
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4 | cut -d. -f1)
COLS=10
ROWS=6
FRAMES=$((COLS * ROWS))
INTERVAL=$((DURATION / FRAMES))
ffmpeg -i input.mp4 -vf "fps=1/${INTERVAL},scale=160:90,tile=${COLS}x${ROWS}" -frames:v 1 seekbar.jpg
```

**High-quality review sheet (320x180 tiles, with padding):**
```bash
ffmpeg -i input.mp4 -vf "fps=1/5,scale=320:180,tile=5x4:padding=4:margin=4" -frames:v 1 review.jpg
```

**Vertical strip (1-wide, useful for timeline previews):**
```bash
ffmpeg -i input.mp4 -vf "fps=1/10,scale=160:90,tile=1x20" -frames:v 1 strip.jpg
```

**Scene-change grid (auto-select visually distinct frames):**
```bash
ffmpeg -i input.mp4 -vf "select='gt(scene,0.4)',scale=320:180,tile=5x4" -vsync vfr -frames:v 1 scenes.jpg
```

**PNG output (lossless, for source material):**
```bash
ffmpeg -i input.mp4 -vf "fps=1,scale=320:180,tile=10x6" -frames:v 1 contact_sheet.png
```

**Multiple sprite sheets (one per minute, every 30 frames per sheet):**
```bash
ffmpeg -i input.mp4 -vf "fps=1,scale=160:90,tile=6x5" -q:v 3 sprites/sheet_%03d.jpg
```
(Remove `-frames:v 1` to get one image per completed tile.)

## Under the Hood

The `tile` filter works by accumulating frames in a buffer. Once it has filled one complete tile (COLS * ROWS frames), it flushes the buffer as a single output image. The filter applies each input frame to the next available cell in left-to-right, top-to-bottom order.

The filter chain `fps=1/10,scale=160:90,tile=10x6` is processed in order:
1. `fps=1/10` — rate-reduces the input to one frame every 10 seconds
2. `scale=160:90` — resizes each frame to 160x90 pixels
3. `tile=10x6` — accumulates 60 resized frames and produces a 1600x540 output image

The output image dimensions are exactly `WIDTH * COLS + padding*(COLS-1) + margin*2` by `HEIGHT * ROWS + padding*(ROWS-1) + margin*2`.

For the **scene-change grid**, the `scene` variable in the `select` filter comes from a lightweight frame-difference heuristic — it computes the mean absolute difference between consecutive frame histograms. The score is 0 for identical frames and approaches 1 for complete scene changes. The value is not calibrated across different content types; a talking head video will rarely exceed 0.2 while an action film will frequently exceed 0.6.

`-frames:v 1` interacts with `tile` by forcing the output to flush the current (potentially incomplete) tile when the stream ends, even if fewer than COLS*ROWS frames were accumulated. The last cells in the grid will be black.

**Seek-bar integration:** A video player using a sprite sheet stores the sheet URL, frame dimensions, and number of columns. To show the thumbnail at time T, it computes `frame_index = floor(T / INTERVAL)`, then `col = frame_index % COLS`, `row = floor(frame_index / COLS)`. It displays the region `(col*W, row*H, W, H)` of the sprite image. This requires only one HTTP request for all thumbnails.

## Sources

- Mux: https://www.mux.com/articles/create-thumbnail-sprite-sheets-with-ffmpeg
- bogotobogo: https://www.bogotobogo.com/FFMpeg/ffmpeg_thumbnails_sprites.php
- GitHub gist (IAmStoxe): https://gist.github.com/IAmStoxe/5ac31a4e954b3ed73d6fae0b9e265b04

## Learned from Usage

- The computed interval must be an integer for the `fps=1/N` filter. For fractional intervals, use `fps=FRAMES/DURATION` (e.g., `fps=60/601` for 60 frames from a 601-second video).
- `-q:v 2` or `-q:v 3` controls JPEG quality for the output sprite. The default is low quality — always set this explicitly for seek-bar sprites used in production.
- For very long videos (2+ hours), use a coarser interval (1/30 or larger). A 10x10 grid from a 3600-second video at 1fps would require loading 36 sheets — users expect a single seek-bar sprite.
- The `thumbnail` filter cannot be combined with `tile` — `thumbnail` picks one frame from N, which breaks the uniform interval expected by seek-bar logic. Use `fps=` for seek bars, `thumbnail` for single best-frame.
- When the video duration is not divisible evenly by the number of cells, the last tile will have empty black cells. This is cosmetically acceptable for contact sheets but may confuse seek-bar logic — pad the expected interval computation to account for it.
- For web delivery, JPEG sprite sheets should be under 200KB for fast loading. At 160x90 per cell, a 10x6 grid (1600x540 JPEG at `-q:v 3`) is typically 50–120KB depending on content complexity.
