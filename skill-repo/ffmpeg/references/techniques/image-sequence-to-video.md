# Image Sequence to Video

## When to Use

Use this technique to convert a numbered series of images into a video. Common use cases: rendering output from animation or simulation software, timelapse photography, slideshows, and converting lossless frame exports to a deliverable format.

## Technique

**`-framerate` before `-i` controls the input read rate — this is NOT the output framerate.** It tells FFmpeg how many images to consume per second of output time. Setting it incorrectly produces video that plays too fast or too slow.

**File naming must be consecutive and zero-padded.** The pattern `%04d` matches `0001.png`, `0002.png`, etc. Gaps in numbering will cause FFmpeg to stop at the first missing file.

**`-pix_fmt yuv420p` is mandatory for web-compatible H.264.** Without it, many players (browsers, QuickTime, mobile) will refuse to play the output because the default pixel format for lossless sources is yuv444p, which H.264 profiles used by these players do not support.

**Slideshow from stills:** Set `-framerate 1/5` (one image every 5 seconds) on the input, then `-r 25` on the output to produce a 25fps video where each frame is held for 5 seconds.

**Timelapse flicker:** Apply `hqdn3d` denoise filter to reduce inter-frame luminance variance caused by auto-exposure variation in cameras.

**Starting from a frame other than 0001:** Use `-start_number N` before `-i` to begin reading from frame N.

**Glob patterns:** If files are not numerically named, use `-pattern_type glob -i "*.png"`. Note: glob pattern support varies by platform and FFmpeg build.

## CLI Commands

**Basic numbered sequence to H.264:**
```bash
ffmpeg -framerate 24 -i frame_%04d.png \
  -c:v libx264 -pix_fmt yuv420p \
  output.mp4
```

**High-quality master (lossless intermediate for further processing):**
```bash
ffmpeg -framerate 24 -i frame_%04d.png \
  -c:v libx264 -preset veryslow -crf 0 -pix_fmt yuv420p \
  output_master.mp4
```

Or use FFV1 for a truly lossless codec:
```bash
ffmpeg -framerate 24 -i frame_%04d.png \
  -c:v ffv1 \
  output_master.mkv
```

**Timelapse with denoising (reduce flicker from auto-exposure):**
```bash
ffmpeg -framerate 30 -i img_%04d.jpg \
  -vf "hqdn3d=4:3:6:4.5" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  timelapse.mp4
```

**Slideshow — each image held for 5 seconds, output at 25fps:**
```bash
ffmpeg -framerate 1/5 -i slide_%04d.jpg \
  -r 25 \
  -c:v libx264 -pix_fmt yuv420p \
  slideshow.mp4
```

**Starting from frame 100 (skipping frames 0001–0099):**
```bash
ffmpeg -start_number 100 -framerate 24 -i frame_%04d.png \
  -c:v libx264 -pix_fmt yuv420p \
  output.mp4
```

**Glob pattern (non-sequential filenames):**
```bash
ffmpeg -framerate 24 -pattern_type glob -i "renders/*.png" \
  -c:v libx264 -pix_fmt yuv420p \
  output.mp4
```

## Under the Hood

FFmpeg's image2 demuxer reads image files as a virtual video stream. `-framerate` (or the alias `-r` before `-i`) sets the virtual framerate of this demuxer, which determines how many seconds of output time each frame occupies. This is distinct from `-r` after `-i`, which sets the output framerate and causes frame duplication or dropping if it differs from the input rate.

The `%04d` pattern is a C-style printf format — `%04d` means a zero-padded integer 4 digits wide. FFmpeg also supports `%d` (no padding) and `%Nd` (N digits).

`hqdn3d` (High Quality Denoise 3D) is a spatial and temporal denoising filter. The four parameters are `luma_spatial`, `chroma_spatial`, `luma_tmp`, `chroma_tmp`. For timelapse flicker, increasing `luma_tmp` (the temporal luma component) has the most visible effect.

`-pix_fmt yuv420p` converts from the input pixel format (often RGB24 for PNG, or YUV444 from some renders) to 4:2:0 chroma subsampling, which is required by the Baseline, Main, and High H.264 profiles used in web and mobile contexts.

## Sources

- Wikibooks (FFmpeg) — image2 demuxer and pattern format reference
- ffmpeg.media — framerate vs output rate distinction
- OTTVerse — pix_fmt yuv420p requirement for H.264 web compatibility
- Shotstack — slideshow framerate technique

## Learned from Usage

- Forgetting `-pix_fmt yuv420p` is the single most common mistake — the video plays fine in VLC but fails in browsers and on iOS.
- `-framerate` must come before `-i`. Placing it after has no effect on the input read rate.
- If FFmpeg stops early, check for a gap in the frame numbering (e.g., `frame_0047.png` missing when sequence runs to 0100).
- For slideshow use cases, the `-framerate 1/5 -r 25` combination is the cleanest approach — it avoids the pad filter and just relies on the demuxer rate vs output rate difference.
