# Convert Audio Format

## When to Use

Use this technique when you need to convert audio between formats — for compatibility, distribution, archival, or size reduction. The technique also applies to extracting audio from video files.

The cardinal rule of audio conversion: **always transcode from a lossless source when possible.** Transcoding from a lossy format (MP3, AAC, OGG) to another lossy format (lossy→lossy) re-introduces compression artifacts on top of existing ones, degrading quality in ways that cannot be undone. If you only have a lossy source, you can still transcode it, but accept that quality is limited by the source.

Lossless formats suitable as sources: WAV, AIFF, FLAC, ALAC (Apple Lossless), PCM.

## Technique

### MP3 Encoding: VBR vs CBR

**VBR (Variable Bitrate)** — recommended for most uses. The encoder allocates bits based on content complexity. Quality is set with `-q:a`:

| `-q:a` value | Approximate bitrate | Use case |
|-------------|--------------------|-|
| 0 | ~245 kbps | Highest quality VBR |
| 2 | ~190 kbps | Standard high quality (recommended) |
| 4 | ~165 kbps | Good quality, smaller file |
| 6 | ~130 kbps | Acceptable, noticeable on critical listening |
| 9 | ~65 kbps | Minimum, poor quality |

Lower `-q:a` = better quality (counterintuitive — it's a quality index, not a compression level).

**CBR (Constant Bitrate)** — use when the target device/system requires a fixed bitrate, or for streaming where consistent file size is important. `-b:a 320k` for maximum MP3 quality.

### AAC Encoding

FFmpeg ships with a built-in AAC encoder (`aac`). It is good but not as efficient as `libfdk_aac`. For most purposes, the native encoder at `-b:a 256k` is indistinguishable from lossless.

`libfdk_aac` (Fraunhofer AAC) is higher quality, especially at lower bitrates. It requires FFmpeg to be compiled with it (it is not included in standard builds due to licensing). Use `-afterburner 1` to enable its quality-enhancement post-processing. If you have it available, prefer it over the native `aac` encoder at any bitrate below 192k.

### FLAC Encoding

FLAC is lossless — no quality decisions to make. `-compression_level` controls encode speed vs file size:
- `0` — fastest, largest files
- `5` — default balance
- `8` — slowest, smallest files (recommended for archival)

FLAC files compressed at level 8 are typically 15–20% smaller than level 0 with no quality difference.

### Format Selection Guide

| Use case | Recommended format |
|----------|--------------------|
| Distribution / streaming | MP3 VBR q:a 2 or AAC 256k |
| Apple ecosystem | AAC 256k (ALAC if lossless) |
| Podcast / voice | MP3 CBR 128k or AAC 128k |
| Archival master | FLAC compression_level 8 |
| Web (HTML5) | OGG Vorbis q:a 6 or Opus 128k |
| Low-latency / real-time | Opus |

**Common mistakes:**
- Transcoding MP3 → AAC → MP3 — each generation adds artifacts. Preserve your lossless masters.
- Using `-ab` (deprecated) instead of `-b:a` — both work in current FFmpeg but `-b:a` is the modern form.
- Forgetting `-vn` when extracting audio from video — by default FFmpeg will try to include video streams, which can cause errors or attach album art unexpectedly.
- Extracting audio with `-c:a copy` from a video when the target format doesn't support the source codec — e.g., extracting AC3 into an MP3 file will fail.
- Using sample rates that don't match the target: AAC for iTunes/Apple requires 44.1kHz or 48kHz; some encoders default to the source sample rate which may be unusual (e.g., 32kHz from a camera).

## CLI Commands

**WAV to MP3 VBR (high quality, recommended for distribution):**
```bash
ffmpeg -i input.wav -c:a libmp3lame -q:a 2 output.mp3
```

**WAV to MP3 CBR 320k (maximum bitrate MP3):**
```bash
ffmpeg -i input.wav -c:a libmp3lame -b:a 320k output.mp3
```

**FLAC to AAC (using native encoder, good for general use):**
```bash
ffmpeg -i input.flac -c:a aac -b:a 256k output.m4a
```

**FLAC to AAC (using libfdk_aac if available, higher quality):**
```bash
ffmpeg -i input.flac -c:a libfdk_aac -b:a 256k -afterburner 1 output.m4a
```

**WAV to OGG Vorbis (open format, good for web):**
```bash
ffmpeg -i input.wav -c:a libvorbis -q:a 6 output.ogg
```

**WAV to FLAC archival (maximum compression):**
```bash
ffmpeg -i input.wav -c:a flac -compression_level 8 output.flac
```

**Extract audio from video (copy stream if compatible):**
```bash
ffmpeg -i input.mp4 -vn -c:a copy output.aac
```

**Extract audio from video and convert to MP3:**
```bash
ffmpeg -i input.mp4 -vn -c:a libmp3lame -q:a 2 output.mp3
```

**Batch convert WAV directory to MP3 (bash):**
```bash
for f in *.wav; do
  ffmpeg -i "$f" -c:a libmp3lame -q:a 2 "${f%.wav}.mp3"
done
```

## Under the Hood

MP3 (MPEG-1 Audio Layer III) uses a psychoacoustic model to discard audio information that human hearing is least sensitive to — frequencies masked by louder nearby frequencies, and sounds at the extremes of the audible range. VBR mode runs this analysis per-frame and allocates bits accordingly; CBR forces a fixed frame size regardless.

AAC (Advanced Audio Coding) was designed as an MP3 successor. It uses a modified discrete cosine transform (MDCT) with a longer window, better stereo coding (joint stereo, intensity stereo, M/S stereo), and more efficient entropy coding. At equivalent bitrates, AAC is generally considered higher quality than MP3.

FLAC uses linear predictive coding (LPC) to model audio as a sequence of predictions, then encodes only the residual (the difference between the prediction and the actual sample) using Rice coding. Higher compression levels use more coefficients for LPC, improving prediction accuracy and reducing residual size at the cost of encode time.

When extracting audio with `-c:a copy`, FFmpeg simply demuxes the audio packets from the container without any decode/encode cycle — this is lossless and near-instant.

## Sources

- trac.ffmpeg.org — Audio Encoding Guide: https://trac.ffmpeg.org/wiki/Encode/Audio
- OTTVerse — Audio Transcoding with FFmpeg: https://ottverse.com/transcode-audio-codec-ffmpeg-without-changing-video/
- FFmpeg Wiki — MP3 Encoding Guide: https://trac.ffmpeg.org/wiki/Encode/MP3

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
