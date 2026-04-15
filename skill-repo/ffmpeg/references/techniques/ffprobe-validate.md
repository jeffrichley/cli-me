# FFprobe Validate

## When to Use

Use this technique when you need to inspect, audit, or validate media files before processing them. Common scenarios include:

- Verifying codec, resolution, bitrate, and frame rate before a transcode pipeline
- Detecting corrupt or unreadable files before a batch job
- Building a CSV audit of a media library
- Compliance checks (e.g., "flag all files not at 1920x1080", "warn if audio bitrate is below 128k")
- Confirming that a completed transcode actually matches the intended spec

`ffprobe` is part of the ffmpeg suite and is always available when ffmpeg is installed. Always prefer `ffprobe` over parsing `ffmpeg` output for metadata — `ffprobe` is designed for machine-readable inspection.

## Technique

### Core Flags

- `-v error` — suppress informational output; only print errors to stderr
- `-print_format json` — output structured JSON instead of default human-readable text
- `-show_format` — include container-level metadata (duration, overall bitrate, filename, format name)
- `-show_streams` — include per-stream metadata (codec, resolution, frame rate, channels, sample rate)
- `-select_streams v:0` — limit output to the first video stream only (use `a:0` for first audio stream)
- `-show_entries` — select specific fields instead of all metadata; reduces output size

### Resolution Shorthand

The combination `-select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0` outputs exactly `1920x1080` (or equivalent) with no surrounding structure. The `s=x` sets the separator to `x`, `p=0` suppresses the stream type prefix.

### r_frame_rate vs avg_frame_rate

- `r_frame_rate` — the frame rate reported by the codec container (e.g., `30000/1001` for 29.97). This is what the file claims.
- `avg_frame_rate` — the computed average across actual frames in the file. For a well-formed file these match. For VFR (variable frame rate) content — common from screen recorders and some cameras — they will differ. When they differ significantly, downstream encoders using `-r` to force a fixed rate may need to insert or drop frames.

### jq for Parsing

`jq` is the standard tool for extracting fields from JSON output. Use `-r` for raw output (no quotes around strings). Use `-e` to return a non-zero exit code when the result is `false` or `null` — this makes compliance checks scriptable in `if` conditions.

### Batch CSV Audit

`find` piped to `parallel` or a `while` loop can run `ffprobe` on every file and accumulate results into a CSV. Use `--` to separate ffprobe flags from the filename when the filename might start with a dash.

## CLI Commands

**Human-readable overview (default output):**
```bash
ffprobe -v quiet -show_format -show_streams input.mp4
```

**Full JSON dump of all streams and format:**
```bash
ffprobe -v error -print_format json -show_format -show_streams input.mp4
```

**Resolution only (outputs e.g. 1920x1080):**
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height \
  -of csv=s=x:p=0 input.mp4
```

**Codec, bitrate, fps, and resolution in one jq query:**
```bash
ffprobe -v error -print_format json -show_streams input.mp4 | \
  jq -r '.streams[] | select(.codec_type=="video") |
    "\(.codec_name) \(.width)x\(.height) \(.avg_frame_rate) \(.bit_rate // "N/A") bps"'
```

**Audio stream info (codec, sample rate, channels, bitrate):**
```bash
ffprobe -v error -print_format json -show_streams input.mp4 | \
  jq -r '.streams[] | select(.codec_type=="audio") |
    "\(.codec_name) \(.sample_rate)Hz \(.channels)ch \(.bit_rate // "N/A") bps"'
```

**Duration in seconds:**
```bash
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 input.mp4
```

**Low bitrate warning (compliance check — exits 1 if video bitrate below 1 Mbps):**
```bash
ffprobe -v error -print_format json -show_streams input.mp4 | \
  jq -e '.streams[] | select(.codec_type=="video") | (.bit_rate // "0" | tonumber) >= 1000000' \
  > /dev/null || echo "WARNING: video bitrate below 1 Mbps"
```

**4K detection (exits 0 if file is 4K or larger):**
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height \
  -print_format json input.mp4 | \
  jq -e '.streams[0].width >= 3840'
```

**Batch CSV audit — codec, resolution, duration for all MKV files:**
```bash
echo "filename,codec,resolution,duration_s" > audit.csv
find . -name "*.mkv" -type f | while IFS= read -r f; do
  info=$(ffprobe -v error -print_format json -show_streams -show_format "$f")
  codec=$(echo "$info" | jq -r '.streams[] | select(.codec_type=="video") | .codec_name' | head -1)
  res=$(echo "$info" | jq -r '.streams[] | select(.codec_type=="video") | "\(.width)x\(.height)"' | head -1)
  dur=$(echo "$info" | jq -r '.format.duration // "N/A"')
  echo "\"$f\",$codec,$res,$dur" >> audit.csv
done
```

**Error-resilient probe (report corrupt or unreadable files):**
```bash
find . -name "*.mp4" -type f | while IFS= read -r f; do
  if ! ffprobe -v error -show_streams "$f" > /dev/null 2>&1; then
    echo "CORRUPT or UNREADABLE: $f"
  fi
done
```

**Check if file has a video stream (exits 0 if yes):**
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_type \
  -of default=noprint_wrappers=1:nokey=1 input.mp4 | grep -q video
```

**All streams summary (type, codec, and index):**
```bash
ffprobe -v error -print_format json -show_streams input.mp4 | \
  jq -r '.streams[] | "\(.index): \(.codec_type) — \(.codec_name)"'
```

## Under the Hood

`ffprobe` opens the container and reads the stream headers without decoding any frames (unless `-count_frames` is used, which is slow). The metadata it reports — codec, resolution, frame rate, bitrate — comes from the container's header records.

The `r_frame_rate` value is stored in the stream header as a rational number (numerator/denominator). For standard 29.97 fps, this is `30000/1001`. The `avg_frame_rate` field is computed by dividing the stream's duration by the number of frames reported in the header. For constant-frame-rate content these match; for VFR they may diverge significantly.

When bitrate is reported as `N/A` in JSON, it means the container does not store per-stream bitrate (common in MKV). In those cases, compute it from file size and duration: `bitrate_bps = file_size_bytes × 8 / duration_seconds`. The `-show_format` `bit_rate` field represents total container bitrate (all streams combined).

`jq -e` sets the process exit code based on the last output value: exit 0 if the result is non-null and not `false`, exit 1 otherwise. This makes it directly usable in shell `if` statements and pipeline health checks.

## Sources

- OTTVerse — "ffprobe Comprehensive Tutorial with 7 Examples": https://ottverse.com/ffprobe-comprehensive-tutorial-with-examples/
- FFmpeg official docs — ffprobe: https://ffmpeg.org/ffprobe.html
- probe.dev — "ffprobe JSON output guide": https://probe.dev/
- Cloudinary — "FFprobe Overview and Usage": https://cloudinary.com/glossary/ffprobe

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
