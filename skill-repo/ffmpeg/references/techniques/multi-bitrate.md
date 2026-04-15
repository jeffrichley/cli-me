# Multi-Bitrate Encoding

## When to Use

Use multi-bitrate encoding whenever you need to produce multiple quality renditions of a source video — for ABR streaming delivery, device-specific downloads, or building a bitrate ladder for HLS/DASH packaging. The key choice is whether to decode the source once or multiple times:

- **Single-decode (split filter):** Decode the source once and pipe to multiple encoders. Use this when the source is expensive to decode (4K ProRes, 8-bit H.264 at high bitrate) or when you want to ensure all renditions are frame-accurate to each other. Slower total wall-clock time per rendition, but total CPU is lower than multiple passes.
- **Multiple ffmpeg invocations:** Simpler, parallelizable, and easier to restart individual renditions. Use when source decode is cheap (e.g., fast SSD + lightweight codec) or when renditions need completely different filter chains.

For HLS/DASH delivery, combine multi-bitrate encoding with keyframe alignment (`-g`, `-keyint_min`, `-sc_threshold 0`) — see the HLS and DASH technique pages.

## Technique

**The `split=N` filter** duplicates the decoded video stream into N identical copies, each of which can be passed through an independent filter chain (scale, deinterlace, etc.) and then to an independent encoder. The filter graph runs in a single ffmpeg process with one decode pass. This avoids re-reading and re-decoding the source file N times.

**Industry bitrate ladder (H.264, 30fps):**

| Resolution | Target bitrate | maxrate (1.07×) | bufsize (2×) | Profile | Level |
|-----------|---------------|----------------|--------------|---------|-------|
| 1080p     | 5000k         | 5350k          | 10000k       | High    | 4.1   |
| 720p      | 2800k         | 2996k          | 5600k        | High    | 3.1   |
| 480p      | 1400k         | 1498k          | 2800k        | Main    | 3.0   |
| 360p      | 800k          | 856k           | 1600k        | Baseline| 3.0   |

These numbers come from Mux and Streaming Learning Center research on actual playback quality vs file size tradeoffs. The `maxrate = 1.07× target` cap prevents brief spikes from blowing past CDN transfer budgets. `bufsize = 2× maxrate` gives the encoder a 2-second buffer window to smooth bitrate across scenes.

**Capped VBR vs CRF:** For delivery where you need predictable file sizes and CDN costs, use capped VBR (`-b:v TARGET -maxrate MAX -bufsize BUF`). For archival or mastering where you want consistent visual quality, use CRF (`-crf N`) with `-maxrate` as a ceiling to prevent runaway bitrate on complex scenes.

**`-movflags +faststart`:** For progressive MP4 download (not streaming), moves the `moov` atom to the beginning of the file. Without this, the browser must download the entire file before it can start playing. Always use for web-delivered MP4 files.

## CLI Commands

### 3 renditions to separate MP4 files, single decode pass

```bash
ffmpeg \
  -i input.mp4 \
  -filter_complex \
    "[0:v]split=3[v1][v2][v3]; \
     [v1]scale=1920:1080:flags=lanczos[v1out]; \
     [v2]scale=1280:720:flags=lanczos[v2out]; \
     [v3]scale=854:480:flags=lanczos[v3out]" \
  -map "[v1out]" \
  -map 0:a \
  -c:v:0 libx264 -profile:v:0 high -level:v:0 4.1 -preset slow \
  -b:v:0 5000k -maxrate:v:0 5350k -bufsize:v:0 10000k \
  -g:v:0 120 -keyint_min:v:0 120 -sc_threshold:v:0 0 \
  -c:a:0 aac -b:a:0 192k -ar:a:0 48000 \
  -movflags +faststart \
  output_1080p.mp4 \
  -map "[v2out]" \
  -map 0:a \
  -c:v:1 libx264 -profile:v:1 high -level:v:1 3.1 -preset slow \
  -b:v:1 2800k -maxrate:v:1 2996k -bufsize:v:1 5600k \
  -g:v:1 120 -keyint_min:v:1 120 -sc_threshold:v:1 0 \
  -c:a:1 aac -b:a:1 128k -ar:a:1 48000 \
  -movflags +faststart \
  output_720p.mp4 \
  -map "[v3out]" \
  -map 0:a \
  -c:v:2 libx264 -profile:v:2 main -level:v:2 3.0 -preset slow \
  -b:v:2 1400k -maxrate:v:2 1498k -bufsize:v:2 2800k \
  -g:v:2 120 -keyint_min:v:2 120 -sc_threshold:v:2 0 \
  -c:a:2 aac -b:a:2 96k -ar:a:2 48000 \
  -movflags +faststart \
  output_480p.mp4
```

### Capped CRF bitrate ladder (quality-based with ceiling)

CRF targets quality; maxrate prevents blowout on complex scenes. Good for archival-quality delivery.

```bash
ffmpeg \
  -i input.mp4 \
  -filter_complex \
    "[0:v]split=4[v1][v2][v3][v4]; \
     [v1]scale=1920:1080:flags=lanczos[v1out]; \
     [v2]scale=1280:720:flags=lanczos[v2out]; \
     [v3]scale=854:480:flags=lanczos[v3out]; \
     [v4]scale=640:360:flags=lanczos[v4out]" \
  -map "[v1out]" -map 0:a \
  -c:v:0 libx264 -profile:v:0 high   -level:v:0 4.1 -preset slow -crf:v:0 18 -maxrate:v:0 6000k -bufsize:v:0 12000k -g:v:0 120 -keyint_min:v:0 120 -sc_threshold:v:0 0 \
  -c:a:0 aac -b:a:0 192k -ar:a:0 48000 \
  -movflags +faststart \
  crf_1080p.mp4 \
  -map "[v2out]" -map 0:a \
  -c:v:1 libx264 -profile:v:1 high   -level:v:1 3.1 -preset slow -crf:v:1 20 -maxrate:v:1 3500k -bufsize:v:1 7000k  -g:v:1 120 -keyint_min:v:1 120 -sc_threshold:v:1 0 \
  -c:a:1 aac -b:a:1 128k -ar:a:1 48000 \
  -movflags +faststart \
  crf_720p.mp4 \
  -map "[v3out]" -map 0:a \
  -c:v:2 libx264 -profile:v:2 main   -level:v:2 3.0 -preset slow -crf:v:2 22 -maxrate:v:2 2000k -bufsize:v:2 4000k  -g:v:2 120 -keyint_min:v:2 120 -sc_threshold:v:2 0 \
  -c:a:2 aac -b:a:2 96k  -ar:a:2 48000 \
  -movflags +faststart \
  crf_480p.mp4 \
  -map "[v4out]" -map 0:a \
  -c:v:3 libx264 -profile:v:3 baseline -level:v:3 3.0 -preset slow -crf:v:3 24 -maxrate:v:3 1000k -bufsize:v:3 2000k  -g:v:3 120 -keyint_min:v:3 120 -sc_threshold:v:3 0 \
  -c:a:3 aac -b:a:3 64k  -ar:a:3 48000 \
  -movflags +faststart \
  crf_360p.mp4
```

### Multi-bitrate directly to HLS in a single command (3 renditions)

This combines multi-bitrate encoding and HLS packaging in one pass. See hls-segments.md for segment format details.

```bash
ffmpeg \
  -i input.mp4 \
  -filter_complex \
    "[0:v]split=3[v1][v2][v3]; \
     [v1]scale=1920:1080:flags=lanczos[v1out]; \
     [v2]scale=1280:720:flags=lanczos[v2out]; \
     [v3]scale=854:480:flags=lanczos[v3out]" \
  -map "[v1out]" -map 0:a \
  -map "[v2out]" -map 0:a \
  -map "[v3out]" -map 0:a \
  -c:v:0 libx264 -profile:v:0 high   -level:v:0 4.1 -preset slow -b:v:0 5000k -maxrate:v:0 5350k -bufsize:v:0 10000k -g:v:0 48 -keyint_min:v:0 48 -sc_threshold:v:0 0 \
  -c:v:1 libx264 -profile:v:1 high   -level:v:1 3.1 -preset slow -b:v:1 2800k -maxrate:v:1 2996k -bufsize:v:1 5600k  -g:v:1 48 -keyint_min:v:1 48 -sc_threshold:v:1 0 \
  -c:v:2 libx264 -profile:v:2 main   -level:v:2 3.0 -preset slow -b:v:2 1400k -maxrate:v:2 1498k -bufsize:v:2 2800k  -g:v:2 48 -keyint_min:v:2 48 -sc_threshold:v:2 0 \
  -c:a:0 aac -b:a:0 192k -ar:a:0 48000 \
  -c:a:1 aac -b:a:1 128k -ar:a:1 48000 \
  -c:a:2 aac -b:a:2 96k  -ar:a:2 48000 \
  -f hls \
  -hls_time 6 \
  -hls_playlist_type vod \
  -hls_flags independent_segments \
  -hls_segment_type mpegts \
  -hls_segment_filename "hls_%v/seg_%03d.ts" \
  -master_pl_name master.m3u8 \
  -var_stream_map "v:0,a:0,name:1080p v:1,a:1,name:720p v:2,a:2,name:480p" \
  hls_%v/playlist.m3u8
```

### 4-rendition ladder with H.265 (HEVC) for higher compression

Use when targeting modern devices where H.265 support is confirmed (most 2016+ mobile devices, all Apple platforms via VideoToolbox).

```bash
ffmpeg \
  -i input.mp4 \
  -filter_complex \
    "[0:v]split=4[v1][v2][v3][v4]; \
     [v1]scale=1920:1080:flags=lanczos[v1out]; \
     [v2]scale=1280:720:flags=lanczos[v2out]; \
     [v3]scale=854:480:flags=lanczos[v3out]; \
     [v4]scale=640:360:flags=lanczos[v4out]" \
  -map "[v1out]" -map 0:a \
  -c:v:0 libx265 -preset slow -crf:v:0 22 -tag:v:0 hvc1 -g:v:0 120 -keyint_min:v:0 120 \
  -c:a:0 aac -b:a:0 192k -ar:a:0 48000 \
  -movflags +faststart \
  hevc_1080p.mp4 \
  -map "[v2out]" -map 0:a \
  -c:v:1 libx265 -preset slow -crf:v:1 24 -tag:v:1 hvc1 -g:v:1 120 -keyint_min:v:1 120 \
  -c:a:1 aac -b:a:1 128k -ar:a:1 48000 \
  -movflags +faststart \
  hevc_720p.mp4 \
  -map "[v3out]" -map 0:a \
  -c:v:2 libx265 -preset slow -crf:v:2 26 -tag:v:2 hvc1 -g:v:2 120 -keyint_min:v:2 120 \
  -c:a:2 aac -b:a:2 96k  -ar:a:2 48000 \
  -movflags +faststart \
  hevc_480p.mp4 \
  -map "[v4out]" -map 0:a \
  -c:v:3 libx265 -preset slow -crf:v:3 28 -tag:v:3 hvc1 -g:v:3 120 -keyint_min:v:3 120 \
  -c:a:3 aac -b:a:3 64k  -ar:a:3 48000 \
  -movflags +faststart \
  hevc_360p.mp4
```

Note: `-tag:v hvc1` is required for Apple device compatibility. Without it, Safari and iOS will not play the HEVC file.

## Under the Hood

**`split=N` filter mechanics:** The `split` filter is a passthrough that outputs N references to the same decoded frame buffer. Each output is an independent stream that can be connected to different sink pads. The frames are not actually duplicated in memory until a downstream filter (like `scale`) writes to them — it uses reference counting. This means CPU savings are mostly in decode, demux, and any upstream filters; each encoder still does its own full encode pass.

**`-map` ordering and stream indices:** When using `filter_complex`, output streams from the filter graph are addressed with their pad labels (`[v1out]`, `[v2out]`, etc.). Each `-map` creates one output stream in the current output file. For multiple output files, each `-map`...`-c:v:N` pair counts stream index N within that output file, resetting to 0 for each new output file argument. This is a common source of confusion when flags like `-c:v:0` appear to apply to the wrong stream.

**`maxrate` and `bufsize` interaction:** These parameters control the H.264 HRD (Hypothetical Reference Decoder) buffer model. The encoder is constrained so that the VBV (Video Buffer Verifier) buffer of size `bufsize` never overflows or underflows. A larger `bufsize` gives the encoder more freedom to vary bitrate over time; a smaller `bufsize` forces tighter CBR-like behavior. The rule of thumb: `bufsize = 2× maxrate` gives the encoder a 2-second smoothing window, which is appropriate for streaming. For broadcast where you need tighter CBR, use `bufsize = 1× maxrate`.

**`-movflags +faststart`:** During encoding, the `moov` atom (which contains the track metadata and sample table needed to play the file) is written at the end of the file because its size is not known until encoding is complete. `+faststart` runs a post-processing step that moves the `moov` atom to the front of the file. This allows the browser to begin playback immediately upon receiving the first bytes, rather than waiting for the entire file to download.

**Scale filter with `flags=lanczos`:** The default ffmpeg scale algorithm is bicubic, which is fast but produces ringing artifacts at sharp edges when downscaling by large factors. Lanczos (`flags=lanczos`) is slower but produces cleaner results at the cost of slight computational overhead. For production delivery, lanczos is worth the extra time.

## Sources

- [OTTVerse: Creating the Perfect Bitrate Ladder for Video Encoding](https://ottverse.com/perfect-bitrate-ladder-for-video-streaming-compression/)
- [Streaming Learning Center: Encoding Ladder Best Practices](https://streaminglearningcenter.com/encoding/building-an-adaptive-bitrate-ladder.html)
- [FFmpeg filter_complex Documentation](https://ffmpeg.org/ffmpeg-filters.html#Filtering-Guide)
- [FFmpeg H.264 Encoding Guide](https://trac.ffmpeg.org/wiki/Encode/H.264)

## Learned from Usage

- When using `split=N` with multiple output files (not a single HLS command), each output file resets stream indexing. `-c:v:0` in the second output file refers to the first video stream in that output, not globally.
- The `scale` filter with named outputs like `[v1out]` must appear in the filter chain before the semicolons: `[v1]scale=1920:1080[v1out]; [v2]scale=1280:720[v2out]`. Putting them on separate lines with backslash continuation works, but the semicolons inside the quoted string are what ffmpeg parses — the shell backslashes are just for readability.
- H.265 (`libx265`) does not accept `-profile:v` the same way H.264 does. Use `-x265-params` for detailed profile control. The `-tag:v hvc1` flag is critical for Apple compatibility — without it, HEVC files play on desktop Chrome but not Safari or iOS.
- `-movflags +faststart` only works for MP4 output. It has no effect on MKV, WebM, or HLS segment files and will produce a warning if applied to them.
- For 4K input with 4-rendition output, expect CPU to be the bottleneck. Use `-preset medium` or `-preset fast` to keep wall-clock time reasonable; the quality difference from `slow` is small at typical streaming bitrates.
