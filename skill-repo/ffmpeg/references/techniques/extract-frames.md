# Extract Frames

## When to Use

Use when you need still images from a video — for thumbnails, poster art, machine learning datasets, storyboards, scene previews, QA screenshots, or sprite sheet source material. Different extraction strategies suit different goals: single best frame, time-based intervals, frame-count intervals, or keyframes only.

## Technique

**Single frame extraction:**
Use `-frames:v 1` to stop after writing one frame. Combine with `-ss` (before `-i` for speed) to target a specific timestamp.

**Automatic best-frame selection with `thumbnail` filter:**
The `thumbnail` filter analyzes the first N frames (default 100) and selects the one with the most distinct color histogram — a heuristic for "interesting frame" that avoids black frames and fades. Ideal for auto-generating a representative thumbnail without knowing the content.

**Interval-based extraction with `fps` filter:**
`fps=1` = one frame per second. `fps=1/5` = one frame every 5 seconds. `fps=1/N` generalizes to one frame every N seconds. This is the simplest approach for evenly-spaced frames.

**Frame-count-based extraction with `select` filter:**
`select='not(mod(n,N))'` selects every Nth frame by frame number (0-indexed). Useful when you want exactly X frames from Y seconds of content. Must be paired with `-vsync vfr` (variable frame rate output) so ffmpeg doesn't duplicate frames to fill gaps.

**I-frame (keyframe) extraction:**
`select='eq(pict_type,I)'` selects only intra-coded frames — frames that don't depend on other frames. Useful for surveillance footage review (each keyframe is a complete scene), or when you want to extract frames at keyframe boundaries (avoids blurry partial-decode artifacts). Also requires `-vsync vfr`.

**Output format:**
- PNG: lossless, larger files. Use for source material, ML datasets, or anything you'll process further.
- JPEG: lossy, smaller files. Use `-q:v 2` for high quality (scale 1–31, lower = better). Good for thumbnails and previews.
- Naming pattern: `%04d` = zero-padded 4-digit number (frame001.jpg, frame002.jpg...). `%06d` for larger sets.

## CLI Commands

**Auto-select best frame from first 100 frames (thumbnail filter):**
```bash
ffmpeg -i input.mp4 -vf "thumbnail" -frames:v 1 thumbnail.jpg
```

**Auto-select best frame, search first 200 frames:**
```bash
ffmpeg -i input.mp4 -vf "thumbnail=200" -frames:v 1 thumbnail.jpg
```

**Single frame at a specific timestamp:**
```bash
ffmpeg -ss 00:00:45 -i input.mp4 -frames:v 1 frame_at_45s.png
```

**High-quality JPEG at timestamp:**
```bash
ffmpeg -ss 00:01:30 -i input.mp4 -frames:v 1 -q:v 2 frame_at_90s.jpg
```

**Every 1 second (fps filter):**
```bash
ffmpeg -i input.mp4 -vf "fps=1" frames/frame_%04d.jpg
```

**Every 5 seconds:**
```bash
ffmpeg -i input.mp4 -vf "fps=1/5" frames/frame_%04d.jpg
```

**Every 10 seconds, lossless PNG:**
```bash
ffmpeg -i input.mp4 -vf "fps=1/10" frames/frame_%04d.png
```

**Every Nth frame by frame number (every 30th frame):**
```bash
ffmpeg -i input.mp4 -vf "select='not(mod(n,30))'" -vsync vfr frames/frame_%04d.png
```

**I-frames (keyframes) only:**
```bash
ffmpeg -i input.mp4 -vf "select='eq(pict_type,I)'" -vsync vfr keyframes/frame_%04d.jpg
```

**Extract frames from a clip range:**
```bash
ffmpeg -ss 00:01:00 -i input.mp4 -t 30 -vf "fps=1" frames/frame_%04d.jpg
```

**Scaled thumbnail (320px wide, maintain aspect ratio):**
```bash
ffmpeg -ss 00:00:30 -i input.mp4 -frames:v 1 -vf "scale=320:-1" thumbnail_320.jpg
```

## Under the Hood

**`thumbnail` filter:** ffmpeg buffers N frames, computes a color histogram for each, and selects the frame whose histogram is furthest from a "boring" baseline. It specifically avoids black frames, heavily repeated colors, and frames during fades. The analysis window is configurable — larger windows find better candidates but buffer more frames in memory.

**`fps` filter:** Operates in the filtergraph's time domain. It produces one output frame per time slot determined by the target framerate. If the source has two frames in a 1-second window, it picks the one closest to the target time. If the source has zero frames (e.g., you asked for 1/60 fps from a 30fps video), it duplicates. The output is a constant-framerate image sequence.

**`select` filter + `-vsync vfr`:** The `select` filter marks frames as "keep" or "discard" based on a Boolean expression. Expressions have access to: `n` (frame number, 0-indexed), `t` (timestamp in seconds), `pict_type` (I/P/B as integer), `scene` (scene change score 0–1), `key` (1 if keyframe). `-vsync vfr` (variable frame rate) tells the output muxer to write each frame with its original timestamp rather than normalizing to a constant rate — required when the frame gaps are irregular.

**`pict_type` values:** I=1, P=2, B=3. The `eq(pict_type,I)` expression selects intra frames. These are the only frames decodable without reference frames — selecting them ensures each extracted image is fully self-contained and artifact-free.

**PNG vs JPEG encoding:** PNG uses lossless LZ77 compression. JPEG uses lossy DCT. For the same perceived quality, JPEG at `-q:v 2` is ~5–10x smaller than PNG. For source material you'll re-process, use PNG. For delivery thumbnails, use JPEG.

## Sources

- OTTVerse — Extract Frames using FFmpeg: https://ottverse.com/extract-frames-using-ffmpeg-a-comprehensive-guide/
- OTTVerse — Thumbnails & Screenshots using FFmpeg: https://ottverse.com/thumbnails-screenshots-using-ffmpeg/
- FFmpeg Wiki — Create thumbnails every X seconds: https://trac.ffmpeg.org/wiki/Create%20a%20thumbnail%20image%20every%20X%20seconds%20of%20the%20video

## Learned from Usage

- Always create the output directory before running frame extraction — ffmpeg will not create missing directories and will silently fail or error on the first write.
- The `thumbnail` filter is surprisingly good for auto-generated preview images. It works well for content with varied scenes; it works poorly for static content (talking heads, screencasts) where all frames look similar.
- `select='not(mod(n,30))'` at 30fps gives you 1 frame per second — equivalent to `fps=1` but controlled by frame count rather than time. Use `fps=` for time-based intervals, `select=` for frame-count-based intervals.
- For ML datasets, PNG is almost always correct — JPEG artifacts can confuse models. The storage cost is worth it.
- `-vsync vfr` is deprecated in newer ffmpeg versions in favor of `-fps_mode vfr`. Both work; use `-fps_mode vfr` if you see deprecation warnings.
- When extracting I-frames for surveillance or scrubbing, the output count is not predictable — it depends on the encoder's GOP (Group of Pictures) structure. A 30-minute recording might yield anywhere from 900 to 54,000 keyframes.
