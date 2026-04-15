# Rotate and Flip

## When to Use

Use rotation and flip filters to correct orientation for videos shot in the wrong direction, mirror footage, or create artistic effects. The most common case is correcting smartphone footage that was shot sideways (90° off) or upside-down (180°).

Before applying a rotation filter, check whether the video has a `rotate` metadata tag — many phones encode a rotation hint rather than actually rotating the pixels. FFmpeg reads this and auto-rotates on decode in newer versions; applying an additional filter rotation will double-rotate the output.

## Technique

**`transpose` filter** — best for 90° increments:

| Value | Effect |
|-------|--------|
| `0` | 90° counter-clockwise + vertical flip |
| `1` | 90° clockwise |
| `2` | 90° counter-clockwise |
| `3` | 90° clockwise + vertical flip |

**180° rotation**: use `hflip,vflip` (equivalent to 180° rotation, no quality loss from pixel resampling).

**`rotate` filter** — for arbitrary angles (non-90° increments). Avoid it for 90° increments because it uses bilinear resampling by default, which softens the image.

**Flip without rotation**:
- `hflip` — horizontal mirror (left-right)
- `vflip` — vertical flip (upside-down)

**Check metadata first**:
```bash
ffprobe -v quiet -select_streams v:0 -show_entries stream_tags=rotate -of default=nw=1 input.mp4
```

## CLI Commands

**90° clockwise (correct a phone video shot in portrait-left orientation):**
```bash
ffmpeg -i input.mp4 \
  -vf "transpose=1" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_cw90.mp4
```

**90° counter-clockwise:**
```bash
ffmpeg -i input.mp4 \
  -vf "transpose=2" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_ccw90.mp4
```

**180° rotation (hflip + vflip, lossless pixel operation):**
```bash
ffmpeg -i input.mp4 \
  -vf "hflip,vflip" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_180.mp4
```

**Horizontal flip (mirror):**
```bash
ffmpeg -i input.mp4 \
  -vf "hflip" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_hflip.mp4
```

**Vertical flip (upside-down):**
```bash
ffmpeg -i input.mp4 \
  -vf "vflip" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_vflip.mp4
```

**Disable auto-rotation from metadata (use `-noautorotate` flag):**
```bash
ffmpeg -noautorotate -i input.mp4 \
  -vf "transpose=1" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_manual_rotate.mp4
```

## Under the Hood

`transpose` is a lossless filter at the pixel data level — it rearranges pixel positions without any interpolation. For 90° rotations this is always the right choice over the `rotate` filter.

`hflip` and `vflip` are also lossless pixel rearrangements. Chaining `hflip,vflip` produces a 180° rotation without any resampling artifact.

The `rotate` filter (e.g., `rotate=45*PI/180`) does use bilinear resampling because arbitrary-angle rotation requires sampling between pixel positions. This introduces slight blurring. For 90° multiples, `transpose` is superior.

Modern FFmpeg (4.0+) reads the `rotate` metadata tag and applies `transpose` automatically during decode. If your source has `rotate=90` in metadata and you also apply `transpose=1`, you'll get a 180° rotated output. Use `-noautorotate` input option to disable this behavior when you want to apply rotation manually.

`ffprobe` stream tag `rotate` holds the metadata rotation value. Common values: `90`, `180`, `270`.

## Sources

- Mux: https://www.mux.com/articles/rotate-a-video-with-ffmpeg
- OTTVerse — Rotate A Video using FFmpeg: https://ottverse.com/rotate-a-video-using-ffmpeg-90-180/
- FFmpeg Filters Documentation: https://ffmpeg.org/ffmpeg-filters.html#transpose
- Cloudinary: https://cloudinary.com/guides/video-effects/ffmpeg-rotate-video

## Learned from Usage

- Smartphone videos almost always have rotation metadata. Check with `ffprobe` before applying `transpose` or you'll likely double-rotate.
- When using `-noautorotate`, the metadata is preserved in the output — players that respect it will auto-rotate again. Strip it with `-metadata:s:v:0 rotate=0` if you want to disable the hint in the output.
- `transpose=1` for 90° CW is the most common correction for a phone held sideways (portrait-right hand position).
- `hflip` is commonly used for mirror/selfie correction when screen-facing cameras record the mirrored view.
