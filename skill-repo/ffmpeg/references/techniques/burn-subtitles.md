# Burn Subtitles (Hard Subs)

## When to Use

Use subtitle burning when you need captions permanently embedded into the video pixels (hard subtitles) — for platforms that don't support separate subtitle tracks, social media autoplay without audio, or accessibility compliance. Use soft subtitles when you want toggleable captions (supported by players that read subtitle tracks, e.g., VLC, YouTube).

## Technique

**Hard subs** (burned into video pixels):
- `subtitles=file.srt` filter requires `libass` (bundled in most FFmpeg builds).
- `force_style=` overrides ASS style properties for font, color, size, and position.
- ASS color format is `&HAABBGGRR` — **BGR, not RGB**, with alpha first. Common gotcha.
- Requires full re-encode of the video stream. You cannot stream-copy (`-c:v copy`) when burning subtitles.
- Windows paths in `subtitles=` require escaping backslashes: `subtitles=C\\:/path/file.srt`.

**Soft subs** (separate subtitle track in container):
- `-c:s mov_text` for MP4/MOV containers (only format MP4 supports).
- `-c:s copy` if remuxing from MKV that already has a subtitle track.
- Does not require re-encoding video.

**SRT to ASS conversion**: `ffmpeg -i input.srt output.ass` — useful for pre-styling before burning.

## CLI Commands

**Basic SRT burn with default styling:**
```bash
ffmpeg -i input.mp4 \
  -vf "subtitles=subtitles.srt" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_hardsub.mp4
```

**Styled captions: white text, black outline, bottom center, 24pt Arial:**
```bash
ffmpeg -i input.mp4 \
  -vf "subtitles=subtitles.srt:force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2'" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_styled_subs.mp4
```
`Alignment=2` = bottom center (ASS numpad alignment). `PrimaryColour=&H00FFFFFF` = white (AABBGGRR: AA=00 opaque, BB=FF blue channel, GG=FF green, RR=FF red = white in BGR).

**ASS subtitle file burn (full ASS styling support):**
```bash
ffmpeg -i input.mp4 \
  -vf "ass=subtitles.ass" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy \
  output_ass_hardsub.mp4
```

**Soft subtitles (embedded track, no re-encode):**
```bash
ffmpeg -i input.mp4 -i subtitles.srt \
  -c:v copy -c:a copy -c:s mov_text \
  -metadata:s:s:0 language=eng \
  output_softsub.mp4
```

**Convert SRT to ASS for pre-styling:**
```bash
ffmpeg -i subtitles.srt subtitles.ass
```
Then edit `subtitles.ass` in a text editor to customize styles, then burn with `ass=subtitles.ass`.

## Under the Hood

The `subtitles` filter passes the subtitle file to `libass` (Advanced SubStation Alpha renderer), which renders each subtitle as vector graphics onto the video frames at the specified position and time. `libass` is a complete ASS renderer — even SRT files are internally converted to ASS before rendering.

`force_style` injects ASS `[V4+ Styles]` properties for the Default style. Only a subset of properties can be overridden this way; for full control, convert to ASS first and edit the style block directly.

The ASS color format `&HAABBGGRR` is a 32-bit hex value where:
- `AA` = alpha (00 = fully opaque, FF = fully transparent — inverted from CSS convention)
- `BB` = blue channel
- `GG` = green channel
- `RR` = red channel

This is little-endian ARGB, not RGBA or RGB. Example: bright yellow = `&H0000FFFF` (AA=00, BB=00, GG=FF, RR=FF).

`mov_text` is the only subtitle codec supported in MP4 containers for soft subs. MKV supports a wider range including `ass`, `srt`, `webvtt`.

## Sources

- Bannerbear: https://www.bannerbear.com/blog/how-to-add-subtitles-to-a-video-using-ffmpeg/
- Cloudinary: https://cloudinary.com/guides/video-effects/ffmpeg-subtitles
- ffmpeg.media: https://ffmpeg.media/blog/burn-subtitles-into-video-with-ffmpeg
- Baeldung: https://www.baeldung.com/linux/ffmpeg-subtitles

## Learned from Usage

- `libass` must be compiled into your FFmpeg build. Verify with `ffmpeg -filters | grep subtitles`. Most package manager builds include it; static builds from ffmpeg.org do too.
- Windows path in filter: backslashes must be double-escaped: `subtitles=C\\\\:/Users/name/file.srt` or use forward slashes `subtitles=C\:/Users/name/file.srt`.
- `Alignment` values follow numpad layout: 1=bottom-left, 2=bottom-center, 3=bottom-right, 7=top-left, 8=top-center, 9=top-right.
- Burning subtitles significantly increases encode time — libass renders each frame individually.
- For vertical (9:16) social video, set `MarginV=150` in `force_style` to keep captions above platform UI overlays.
