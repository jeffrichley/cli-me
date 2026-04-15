# Surveillance Clip

## When to Use

Use when working with security camera footage, dashcam recordings, or any time-based archive where you need to: extract a clip from a single recording file, stitch segments from a rolling archive, detect motion events, or set up a continuous recording pipeline. Common scenarios: "pull the clip from 2:15 PM to 2:30 PM", "record 30-minute rolling archive", "find all motion events in this footage".

## Technique

**Single file extraction:**
Use `-ss` (before `-i`) + `-to` or `-t` with `-c copy` for fast, lossless extraction. The keyframe alignment issue matters less here — most surveillance cameras encode at 1–2 second keyframe intervals, so drift is small. Add `-avoid_negative_ts make_zero` to prevent timestamp issues.

**Segmented archive with concat demuxer:**
Surveillance systems often record in segments (e.g., one file per 10 minutes). To extract a clip that spans multiple files, use the concat demuxer:
1. Create a `filelist.txt` listing source files in order
2. Run `ffmpeg -f concat -safe 0 -i filelist.txt ...`

The `filelist.txt` format is:
```
file '/absolute/path/to/segment1.mp4'
file '/absolute/path/to/segment2.mp4'
```
`-safe 0` is required when using absolute paths.

**Motion detection with `select` + `metadata=print`:**
The `select` filter with `scene` score is a lightweight motion proxy. A two-pass approach works best:
- Pass 1: `select='gt(scene,0.1)',metadata=print:file=motion_log.txt` — scan the full file, log timestamps of frames with motion-like scene changes
- Pass 2: Use the log to extract specific time ranges

True motion detection uses the `mpdecimate` or `mestimate` filters, but scene-change score is simpler and sufficient for many surveillance review tasks.

**Buffer padding around events:**
When extracting motion event clips, always pad before and after the detected timestamp:
```
start = event_time - BUFFER (e.g., 10 seconds)
end = event_time + BUFFER (e.g., 30 seconds)
```
This ensures the clip shows what triggered the event and what happened immediately after.

**Rolling archive with shell loop:**
Use ffmpeg's `-t` (duration per segment) + shell loop to write continuous rolling files. Pair with a cleanup loop that deletes files older than N minutes/hours. Use `-strftime 1` with a time-pattern filename to embed the recording timestamp directly in the filename.

**`-strftime 1` for timestamp filenames:**
Enables `strftime`-style format codes in the output filename:
- `%Y` = year, `%m` = month, `%d` = day
- `%H` = hour, `%M` = minute, `%S` = second
- Example: `recording_%Y%m%d_%H%M%S.mp4`

## CLI Commands

**Extract clip from single file (fast, stream copy):**
```bash
ffmpeg -ss 00:15:00 -i recording.mp4 -to 00:30:00 -c copy -avoid_negative_ts make_zero clip.mp4
```

**Extract with buffer padding (event at 15:00, ±30s):**
```bash
ffmpeg -ss 00:14:30 -i recording.mp4 -to 00:15:30 -c copy -avoid_negative_ts make_zero event_clip.mp4
```

**Create filelist.txt for multi-segment extraction:**
```bash
# Build filelist.txt
printf "file '%s'\n" /recordings/cam1_14h50.mp4 /recordings/cam1_15h00.mp4 /recordings/cam1_15h10.mp4 > filelist.txt

# Extract spanning segment from 14:55 to 15:05 (10 minutes across two files)
ffmpeg -f concat -safe 0 -i filelist.txt -ss 00:05:00 -t 600 -c copy output_clip.mp4
```
Note: `-ss` here is relative to the start of the concatenated stream (not the original file timestamps).

**Full cross-segment extraction with absolute timestamps:**
```bash
# If segments are named with timestamps, compute offset manually
# cam1_14h50.mp4 starts at 14:50:00, target starts at 14:55:00 → offset = 5 minutes
ffmpeg -f concat -safe 0 -i filelist.txt -ss 00:05:00 -to 00:15:00 -c copy clip.mp4
```

**Rolling archive recording (10-minute segments with timestamps in filename):**
```bash
ffmpeg -i rtsp://camera_ip/stream \
  -c copy \
  -f segment \
  -segment_time 600 \
  -segment_format mp4 \
  -strftime 1 \
  "/recordings/cam1_%Y%m%d_%H%M%S.mp4"
```

**Shell loop for rolling archive with cleanup:**
```bash
#!/bin/bash
ARCHIVE_DIR="/recordings/cam1"
KEEP_HOURS=24
mkdir -p "$ARCHIVE_DIR"

# Start recording in background
ffmpeg -i rtsp://camera_ip/stream \
  -c copy -f segment -segment_time 600 -segment_format mp4 -strftime 1 \
  "$ARCHIVE_DIR/segment_%Y%m%d_%H%M%S.mp4" &

FFMPEG_PID=$!

# Rolling cleanup loop
while kill -0 $FFMPEG_PID 2>/dev/null; do
  find "$ARCHIVE_DIR" -name "segment_*.mp4" -mmin +$((KEEP_HOURS * 60)) -delete
  sleep 60
done
```

**Motion detection pass (log frame timestamps):**
```bash
ffmpeg -i recording.mp4 \
  -vf "select='gt(scene,0.15)',metadata=print:file=motion_events.txt" \
  -an -f null /dev/null
```
The output file `motion_events.txt` lists each selected frame with its `pts_time` (timestamp in seconds).

**Extract clips around detected motion events (from log):**
```bash
# motion_events.txt has lines like: frame:42 pts:1234.567000 pts_time:1234.567
grep "pts_time" motion_events.txt | awk -F: '{print $2}' | while read ts; do
  START=$(echo "$ts - 10" | bc)
  END=$(echo "$ts + 30" | bc)
  OUTFILE="event_${ts}.mp4"
  ffmpeg -ss "$START" -i recording.mp4 -t 40 -c copy "$OUTFILE"
done
```

## Under the Hood

**Concat demuxer vs concat filter:**
- Concat demuxer (`-f concat -i filelist.txt`): reads multiple files as a single virtual input. Operates at the packet level — no decoding required when using `-c copy`. Timestamps are adjusted so the second file starts where the first ends. Best for surveillance archive stitching.
- Concat filter (`[0:v][1:v]concat=n=2:v=1:a=1`): operates in the decoded frame domain, re-encodes output. Required for synchronized A/V concatenation with different codecs. Not used for surveillance workflows.

**`-f segment` output format:**
The segment muxer writes a sequence of output files, cutting at the specified `segment_time` boundary (rounded to the next keyframe). The `-strftime 1` flag enables format string substitution in the output filename using the wall-clock time at the moment each segment starts. This makes segment filenames directly usable for timestamp-based retrieval: given a target time T, the correct segment file can be found by filename without reading file metadata.

**`select` + `metadata=print`:**
The `select` filter evaluates its expression for each frame. When using `metadata=print:file=log.txt`, it writes a line to the log for every frame that passes the filter, including `pts_time` (the frame's presentation timestamp in seconds from the start of the file). This is not a full motion detection algorithm — it uses inter-frame scene change score, which is a histogram difference. Real motion (an object moving across frame) will score differently depending on object size and background complexity. Threshold tuning is empirical.

**`-avoid_negative_ts make_zero` in surveillance context:**
Surveillance cameras typically encode with hardware encoders that set keyframe intervals based on wall time (e.g., every 2 seconds). Stream copy extracts start at the nearest keyframe before the requested time, which may have a slightly earlier timestamp than the requested start. `make_zero` shifts timestamps so the first packet in the output is at 0:00, preventing downstream tools from treating the clip as starting at a negative timestamp.

## Sources

- FFmpeg-Detect-Copy-Motion GitHub: https://github.com/zodrzodr/FFmpeg-Detect-Copy-Motion
- Mux: https://www.mux.com/articles/ffmpeg-segment-recording
- FFmpeg documentation: https://ffmpeg.org/ffmpeg-formats.html#concat
- FFmpeg documentation: https://ffmpeg.org/ffmpeg-formats.html#segment_002c-stream_005fsegment_002c-ssegment

## Learned from Usage

- The concat demuxer requires `-safe 0` for absolute paths. For relative paths you can omit it, but absolute paths are always safer in automated scripts.
- When working with RTSP streams, add `-rtsp_transport tcp` before `-i` to prefer TCP over UDP — UDP drops frames on congested networks: `ffmpeg -rtsp_transport tcp -i rtsp://...`
- Surveillance recordings often have variable frame rates and broken timestamps from hardware encoders. If concat or extraction produces A/V sync drift, add `-vsync cfr` to normalize: `ffmpeg -f concat -safe 0 -i filelist.txt -vsync cfr output.mp4`
- For the scene-change motion detection pass, threshold 0.10–0.15 works well for outdoor cameras with moderate activity. Lower the threshold (0.05) for indoor static-background cameras. Always tune on a sample of your actual footage.
- `-strftime 1` filenames with `%S` granularity can collide if segments are very short. Use `%Y%m%d_%H%M%S` as the minimum safe pattern.
- When building a clip extraction tool around a rolling archive, sort `filelist.txt` entries by filename (which sorts by timestamp if using `strftime` naming) — do not rely on filesystem mtime, which can shift after file moves or copies.
