# Convert Video Format

## When to Use

Use this technique when you need to change a video's container format (e.g., MKV to MP4) or re-encode a video into a different codec. The critical decision upfront is whether to **transmux** (copy streams without re-encoding) or **re-encode** (decode and re-compress). Transmux is always preferred when compatible — it is lossless, near-instant, and produces no quality loss. Re-encoding is necessary when the source codec is incompatible with the target container, when quality or file size adjustments are needed, or when preparing video for a specific platform.

## Technique

**Step 1 — Probe the source first.**

Always run `ffprobe` before deciding on a strategy. You need to know the video codec, audio codec, and pixel format before choosing whether to transmux or re-encode.

```
ffprobe -v quiet -print_format json -show_streams input.mkv
```

Key fields to check:
- `codec_name` on the video stream (h264, hevc, av1, vp9, etc.)
- `codec_name` on the audio stream (aac, mp3, ac3, pcm_s16le, flac, etc.)
- `pix_fmt` (yuv420p, yuv422p, yuv444p, etc.)

**Step 2 — Transmux if possible.**

If the source video codec is already compatible with the target container, use `-c copy`. This is instant and lossless.

MP4 container supports: H.264, H.265/HEVC, AAC, MP3, AC3, EAC3.
MP4 does NOT support: PCM audio (`pcm_s16le`, `pcm_s24le`, etc.), FLAC, Opus (in most players), or most raw formats.

If your source has PCM audio and you want MP4, you must re-encode the audio to AAC even if you copy the video.

**Step 3 — Re-encode when necessary.**

When re-encoding to H.264 for broad compatibility:
- Always add `-pix_fmt yuv420p` — many sources use yuv444p or yuv422p which H.264 technically supports but most devices/players reject.
- Always add `-movflags +faststart` for MP4 output — this moves the moov atom to the front of the file, enabling streaming/progressive download before the full file is downloaded.
- Use `-crf 23` as the default quality setting (18–28 is the practical range).

**Common mistakes:**
- Using `-c copy` when the source audio is PCM and the target is MP4 — this either fails outright or produces a file with broken audio.
- Forgetting `-pix_fmt yuv420p` — results in playback failures on phones, smart TVs, and older players.
- Forgetting `-movflags +faststart` for web-destined MP4 files — the video won't start playing until fully downloaded.
- Using CRF 0 (lossless) for "archival" — lossless H.264 produces enormous files; use CRF 18 for high-quality archival instead.

## CLI Commands

**Transmux MKV to MP4 (lossless, instant):**
```bash
ffmpeg -i input.mkv -c copy -movflags +faststart output.mp4
```

**Transmux MKV to MP4 with PCM audio fix (copy video, re-encode audio only):**
```bash
ffmpeg -i input.mkv -c:v copy -c:a aac -b:a 192k -movflags +faststart output.mp4
```

**Re-encode MOV to MP4 (standard quality, broad compatibility):**
```bash
ffmpeg -i input.mov -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 192k \
  -pix_fmt yuv420p -movflags +faststart output.mp4
```

**High-quality archival encode (visually lossless):**
```bash
ffmpeg -i input.mov -c:v libx264 -crf 18 -preset slow -c:a aac -b:a 320k \
  -pix_fmt yuv420p -movflags +faststart output.mp4
```

**Batch convert a directory of MKV files to MP4 (bash):**
```bash
for f in *.mkv; do
  ffmpeg -i "$f" -c copy -movflags +faststart "${f%.mkv}.mp4"
done
```

**Batch re-encode directory to H.264 MP4 (bash):**
```bash
for f in *.mov; do
  ffmpeg -i "$f" -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 192k \
    -pix_fmt yuv420p -movflags +faststart "${f%.mov}.mp4"
done
```

## Under the Hood

When you use `-c copy`, FFmpeg reads the compressed packets from the source container and writes them directly into the target container without touching the codec data. No decode/encode cycle occurs. The only work done is remuxing — rewriting the container structure.

When you re-encode with `libx264`, FFmpeg fully decodes each frame to raw YUV, passes it through the x264 encoder which applies DCT, quantization, motion estimation, and entropy coding, then writes the resulting H.264 bitstream into the output container.

`-movflags +faststart` works by running a post-processing step after the encode finishes: FFmpeg reads the completed MP4, relocates the `moov` atom (which contains all metadata and index information) from the end of the file to the beginning, and rewrites the file. This is why you'll see the output file briefly appear and then be rewritten when encoding to MP4 with this flag.

`-pix_fmt yuv420p` forces chroma subsampling to 4:2:0, meaning chroma channels are stored at half the resolution of luma in both horizontal and vertical dimensions. This is the universal compatibility baseline for H.264 playback across all consumer devices.

## Sources

- OTTVerse — "Convert MKV to MP4 Using FFmpeg": https://ottverse.com/how-to-convert-mkv-to-mp4-using-vlc-ffmpeg-handbrake/
- Bannerbear — "Converting Video and Audio Formats Using FFmpeg": https://www.bannerbear.com/blog/converting-video-and-audio-formats-using-ffmpeg/
- avpres.net — FFmpeg container format notes: https://avpres.net/FFmpeg/

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
