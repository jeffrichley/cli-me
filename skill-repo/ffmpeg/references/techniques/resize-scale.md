# Resize and Scale

## When to Use

Use scaling when you need to change the output resolution of a video — whether to hit a delivery spec (1080p, 720p, 4K), reduce file size, or fit a platform's dimension requirements. Scale filters are also required whenever you change aspect ratio or letterbox content to an exact canvas size.

## Technique

FFmpeg's `scale` filter handles all resizing. Key rules:

- Use `-2` (not `-1`) for the auto-calculated dimension — `-1` can produce odd numbers that break H.264 encoding. `-2` rounds to the nearest even number.
- Use `flags=lanczos` for high-quality downscaling (sharper than the default `bicubic` at large size reductions).
- Use `force_original_aspect_ratio=decrease,pad` to letterbox into an exact canvas without cropping.
- Always output `-pix_fmt yuv420p` for maximum player compatibility (required by H.264, expected by most platforms).

## CLI Commands

**Scale to 1080p width, height auto (width-fixed):**
```bash
ffmpeg -i input.mp4 \
  -vf "scale=1920:-2:flags=lanczos" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  output_1080p.mp4
```

**Scale to 720p height, width auto (height-fixed):**
```bash
ffmpeg -i input.mp4 \
  -vf "scale=-2:720:flags=lanczos" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  output_720p.mp4
```

**Letterbox to exact 1920x1080 (preserves aspect ratio, adds black bars):**
```bash
ffmpeg -i input.mp4 \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  output_letterboxed.mp4
```

**High-quality lanczos downscale to 480p:**
```bash
ffmpeg -i input.mp4 \
  -vf "scale=-2:480:flags=lanczos+accurate_rnd" \
  -c:v libx264 -crf 20 -preset slow -pix_fmt yuv420p \
  output_480p.mp4
```

## Under the Hood

The `scale` filter uses libswscale internally. The `flags` parameter maps directly to swscale algorithm constants: `lanczos` uses a windowed sinc function with a Lanczos kernel — computationally heavier than `bicubic` or `bilinear` but produces visibly better results when shrinking by more than 50%.

The `-2` shorthand tells the filter to auto-calculate the dimension but round up to the nearest even integer. H.264 (and most YUV chroma subsampling formats) require even-numbered dimensions because chroma planes are subsampled at 2x in both directions.

`force_original_aspect_ratio=decrease` shrinks the input to fit within the target box without cropping. The subsequent `pad` centers it on the canvas by computing `(ow-iw)/2` (horizontal offset) and `(oh-ih)/2` (vertical offset).

## Sources

- OTTVerse: https://ottverse.com/ffmpeg-scale-filter/
- Mux: https://www.mux.com/articles/ffmpeg-video-scaling
- Creatomate: https://creatomate.com/blog/how-to-resize-a-video-using-ffmpeg

## Learned from Usage

- `-1` for auto-dimension will fail with `width/height not divisible by 2` on H.264; always use `-2`.
- `lanczos` adds noticeable encoding time — use `bicubic` for fast preview encodes.
- When letterboxing, the `pad` filter color defaults to black; use `pad=...:color=white` for white bars.
- The `scale2ref` filter exists for scaling one stream relative to another (useful for watermarks).
