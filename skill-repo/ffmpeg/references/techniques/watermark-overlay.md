# Watermark Overlay

## When to Use

Use overlays to composite a logo, watermark, bug, or lower-third onto a video. Common use cases: brand logo in corner, semi-transparent copyright notice, timed intro/outro bug, scaled product watermark.

## Technique

Two-input compositing requires `-filter_complex` (not `-vf`). The two inputs are referenced as `[0:v]` (video) and `[1:v]` (overlay image).

**Position variables** available in the `overlay` filter:
- `W`, `H` — dimensions of the main video
- `w`, `h` — dimensions of the overlay image
- `main_w`, `main_h`, `overlay_w`, `overlay_h` — verbose aliases

Common positions:
- Bottom-right: `x=W-w-10:y=H-h-10` (10px margin)
- Bottom-left: `x=10:y=H-h-10`
- Top-right: `x=W-w-10:y=10`
- Center: `x=(W-w)/2:y=(H-h)/2`

**Opacity** is set by pre-processing the overlay with `colorchannelmixer=aa=0.5` (50% alpha) before passing it to `overlay`.

**Scaling the logo** before overlay: use `[1:v]scale=200:-1[logo]` to resize the watermark to 200px wide before compositing.

**Timed overlay**: use `enable='between(t,0,5)'` on the overlay filter to show it only during seconds 0–5.

## CLI Commands

**Bottom-right watermark with 10px margin:**
```bash
ffmpeg -i input.mp4 -i logo.png \
  -filter_complex "[0:v][1:v]overlay=W-w-10:H-h-10" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_watermarked.mp4
```

**Semi-transparent watermark (50% opacity):**
```bash
ffmpeg -i input.mp4 -i logo.png \
  -filter_complex "[1:v]colorchannelmixer=aa=0.5[logo];[0:v][logo]overlay=W-w-10:H-h-10" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_transparent_wm.mp4
```

**Scaled logo (resize to 150px wide) at top-right:**
```bash
ffmpeg -i input.mp4 -i logo.png \
  -filter_complex "[1:v]scale=150:-1[logo];[0:v][logo]overlay=W-w-10:10" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_scaled_wm.mp4
```

**Timed overlay: show logo only from t=0 to t=5 seconds:**
```bash
ffmpeg -i input.mp4 -i logo.png \
  -filter_complex "[1:v]scale=150:-1[logo];[0:v][logo]overlay=W-w-10:H-h-10:enable='between(t,0,5)'" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_timed_wm.mp4
```

## Under the Hood

`-filter_complex` is required when combining two separate input streams. It creates a named filter graph where streams are labeled `[0:v]`, `[1:v]`, etc. Named intermediate outputs like `[logo]` are connected by name between filter stages.

The `overlay` filter composites `[1:v]` onto `[0:v]` using alpha compositing if the overlay has an alpha channel (PNG). Without an alpha channel (JPEG logos), the overlay is fully opaque regardless of `colorchannelmixer`.

`colorchannelmixer=aa=0.5` scales the alpha channel of the overlay to 50%. The `aa` parameter is the alpha-to-alpha gain coefficient. This requires the input image to have an alpha channel (PNG, WebP with alpha). A JPEG watermark has no alpha channel and `colorchannelmixer` will not make it transparent.

`enable='between(t,0,5)'` uses FFmpeg's timeline editing — a filter-level conditional that disables the filter outside the specified time range, effectively making the overlay invisible outside those seconds.

## Sources

- Mux: https://www.mux.com/articles/ffmpeg-watermark
- OTTVerse: https://ottverse.com/ffmpeg-overlay-filter-watermark/
- Cloudinary: https://cloudinary.com/guides/video-effects/ffmpeg-watermark
- Bannerbear: https://www.bannerbear.com/blog/how-to-add-a-watermark-to-video-using-ffmpeg/

## Learned from Usage

- PNG with transparency is required for opacity effects. JPEG logos appear as solid rectangles.
- `[1:v][0:v]overlay` vs `[0:v][1:v]overlay` — the overlay filter takes `base,overlay` order: first input is the background, second is what gets composited on top. Input order in the filter_complex label matters.
- When chaining scale + colorchannelmixer + overlay, each step must pass its labeled output to the next stage explicitly.
- For a bottom-center position: `x=(W-w)/2:y=H-h-20`.
- `scale2ref` can size the logo relative to the video dimensions, e.g., always 10% of video width.
