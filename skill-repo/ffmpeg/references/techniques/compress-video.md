# Compress Video

## When to Use

Use this technique when you need to reduce a video's file size — for storage, upload limits, streaming bandwidth, or delivery requirements. The right approach depends on whether you have a quality target (use CRF) or a file size target (use two-pass encoding).

**CRF (Constant Rate Factor)** — use when you want the best quality at the smallest file size and don't need to hit a specific size. The encoder varies bitrate as needed to maintain perceptual quality.

**Two-pass** — use when you have a hard file size limit (e.g., email attachment, social media upload cap, client delivery spec). Two-pass is slower but achieves a precise average bitrate across the file.

## Technique

### CRF Scale by Codec

| Codec | CRF Range | Default | Visually Lossless | Notes |
|-------|-----------|---------|-------------------|-------|
| x264 (H.264) | 0–51 | 23 | ~18 | 0 = lossless (huge), 51 = worst |
| x265 (H.265/HEVC) | 0–51 | 28 | ~24 | Equivalent quality to x264 at ~half the bitrate |
| VP9 | 0–63 | — | ~31 | Must also set `-b:v 0` to enable CRF mode |
| AV1 (libaom) | 0–63 | — | ~23 | Slow encoder; use `-cpu-used 4` for reasonable speed |
| AV1 (libsvtav1) | 0–63 | — | ~28 | Much faster than libaom; recommended for practical AV1 |

**The ±6 rule:** Every ±6 CRF units roughly doubles or halves the file size while maintaining comparable quality. Going from CRF 23 to CRF 17 will approximately double the file size. Going from 23 to 29 will roughly halve it.

### Preset Tradeoffs

The `-preset` option (x264/x265) controls encode speed vs compression efficiency. Slower presets produce smaller files at the same CRF.

| Preset | Encode Speed | File Size vs Medium |
|--------|-------------|---------------------|
| ultrafast | Very fast | ~40% larger |
| superfast | Fast | ~30% larger |
| veryfast | Fast | ~20% larger |
| faster | Moderate | ~10% larger |
| fast | Moderate | ~5% larger |
| medium | Default | baseline |
| slow | Slow | ~10% smaller |
| slower | Very slow | ~15% smaller |
| veryslow | Very slow | ~20% smaller |

For most use cases, `medium` or `slow` is the right balance. `slow` gives 10–15% smaller output than `medium` with 2–3x the encode time. `veryslow` rarely justifies the time cost over `slow` for practical use.

### Two-Pass Target File Size

Formula to calculate target video bitrate:

```
video_kbps = (target_MB × 8192 / duration_seconds) - audio_kbps
```

Example: 100 MB target, 10-minute video (600 seconds), 192k audio:
```
video_kbps = (100 × 8192 / 600) - 192 = 1365 - 192 = 1173 kbps
```

Two-pass always requires running FFmpeg twice — the first pass analyzes the video and writes a stats file, the second pass uses that analysis to hit the target bitrate.

**Common mistakes:**
- Using CRF 0 thinking it means "lossless" in a useful sense — it does produce lossless H.264, but the file can be larger than the uncompressed source.
- Combining `-crf` and `-b:v` with a non-zero bitrate — this activates "constrained CRF" mode, which caps bitrate but often produces unexpected results. Set `-b:v 0` explicitly with VP9 CRF to disable the cap.
- Running only the first pass of a two-pass encode and using that output — the first pass output is intentionally low quality (placeholder).
- Forgetting to delete the `ffmpeg2pass-0.log` stats file between unrelated two-pass encodes — it will use stale analysis data.
- Using x265 with `-pix_fmt yuv420p` when the output will only be played on modern devices — x265 supports yuv420p10le (10-bit) which gives better quality, but yuv420p (8-bit) is the safe default for compatibility.

## CLI Commands

**H.264 CRF encode (default quality, broad compatibility):**
```bash
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset medium \
  -c:a aac -b:a 192k -pix_fmt yuv420p -movflags +faststart output.mp4
```

**H.264 CRF encode (high quality, slower):**
```bash
ffmpeg -i input.mp4 -c:v libx264 -crf 18 -preset slow \
  -c:a aac -b:a 256k -pix_fmt yuv420p -movflags +faststart output.mp4
```

**H.265/HEVC CRF encode (same quality as H.264 at ~half the bitrate):**
```bash
ffmpeg -i input.mp4 -c:v libx265 -crf 28 -preset medium \
  -c:a aac -b:a 192k -pix_fmt yuv420p -movflags +faststart output.mp4
```

**Two-pass H.264 for target file size (replace TARGET_KBPS with calculated value):**
```bash
# Pass 1
ffmpeg -y -i input.mp4 -c:v libx264 -b:v TARGET_KBPSk -pass 1 \
  -an -f null /dev/null    # Windows: use NUL instead of /dev/null

# Pass 2
ffmpeg -i input.mp4 -c:v libx264 -b:v TARGET_KBPSk -pass 2 \
  -c:a aac -b:a 192k -pix_fmt yuv420p -movflags +faststart output.mp4
```

**VP9 CRF encode (good for web, open codec):**
```bash
ffmpeg -i input.mp4 -c:v libvpx-vp9 -crf 31 -b:v 0 \
  -c:a libopus -b:a 128k output.webm
```

**AV1 encode with libsvtav1 (best compression, modern decoders required):**
```bash
ffmpeg -i input.mp4 -c:v libsvtav1 -crf 28 -preset 6 \
  -c:a libopus -b:a 128k output.mkv
```

## Under the Hood

CRF works by targeting a constant perceptual quality level rather than a constant bitrate. The encoder uses a quantization parameter (QP) internally, and CRF is a quality-relative wrapper around it. In x264, CRF 23 maps to a QP of ~23 on flat scenes and adjusts per-frame based on complexity — complex scenes get lower QP (less compression) to maintain quality, simple scenes get higher QP (more compression) because the loss is less perceptible.

Two-pass encoding works differently: pass 1 decodes every frame, runs motion estimation, and writes a statistics file describing the complexity of each portion of the video. Pass 2 reads this statistics file and distributes the bitrate budget across the video — giving more bits to complex scenes and fewer to simple ones — so the average bitrate matches the target while perceptual quality is maximized.

The preset system in x264/x265 controls the depth of motion estimation, the number of reference frames, the subpixel refinement level, and other CPU-intensive analysis steps. Slower presets do more analysis and find better encodings, but the law of diminishing returns applies heavily past `slow`.

## Sources

- slhck.info — "Understanding Rate Control Modes": https://slhck.info/video/2017/02/24/crf-guide.html
- Mux — "How to Compress Video Files While Maintaining Quality with FFmpeg": https://www.mux.com/articles/how-to-compress-video-files-while-maintaining-quality-with-ffmpeg
- Vibbit — "FFmpeg CRF Examples: H.264, H.265, VP9 & AV1": https://vibbit.ai/blog/ffmpeg-crf-examples

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
