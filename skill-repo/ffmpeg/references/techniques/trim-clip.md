# Trim Clip

## When to Use

Use when you need to cut a specific segment out of a video or audio file — removing the beginning, end, or middle of a clip. This is the most common ffmpeg operation, and the most misunderstood because of `-ss` placement.

## Technique

The position of `-ss` (seek / start time) relative to `-i` (input) is THE critical decision in ffmpeg trimming:

**`-ss` BEFORE `-i` (input seeking):**
- ffmpeg seeks to the nearest keyframe before the target time, then starts reading
- Fast — skips decoding the unused portion
- Slightly inaccurate — start may be a few frames off depending on keyframe interval
- Required when using `-c copy` (stream copy), because stream copy cannot create new keyframes

**`-ss` AFTER `-i` (output seeking):**
- ffmpeg decodes from the very beginning of the file up to the start point
- Slow on long files — decodes and discards all frames before the target
- Accurate — can seek to any exact frame
- Use when frame accuracy matters more than speed

**Best of both worlds — fast AND frame-accurate:**
Use `-ss` before `-i` for fast seeking, but re-encode (do NOT use `-c copy`). ffmpeg will:
1. Jump to the nearest keyframe (fast)
2. Re-encode from that point forward, so the output starts at exactly the requested frame

**`-t` vs `-to`:**
- `-t <duration>` — output duration (seconds or HH:MM:SS). Example: `-t 30` = 30-second clip
- `-to <timestamp>` — end timestamp in the output. Example: `-to 00:01:30`
- When `-ss` is before `-i`, use `-to <timestamp-in-source>` for end position — the output timestamps reset to 0

**Stream copy (`-c copy`) gotcha:**
Stream copy can only cut at existing keyframe boundaries. If you cut to a non-keyframe position, ffmpeg silently adjusts to the nearest keyframe. Use `-avoid_negative_ts make_zero` to prevent timestamp issues when the nearest keyframe is before your requested start.

## CLI Commands

**Fast rough cut (stream copy, nearest keyframe):**
```bash
ffmpeg -ss 00:01:00 -i input.mp4 -to 00:02:30 -c copy -avoid_negative_ts make_zero output.mp4
```

**Frame-accurate cut (re-encode, slow on long files):**
```bash
ffmpeg -i input.mp4 -ss 00:01:00 -to 00:02:30 output.mp4
```

**Fast + frame-accurate (best of both — -ss before -i + re-encode):**
```bash
ffmpeg -ss 00:01:00 -i input.mp4 -to 00:02:30 output.mp4
```
Note: `-to` here is relative to the source file, not the output. Output will start at 0:00.

**Duration-based cut (30 seconds starting at 1 minute):**
```bash
ffmpeg -ss 00:01:00 -i input.mp4 -t 30 -c copy output.mp4
```

**Cut with explicit codec (H.264 re-encode, fast + accurate):**
```bash
ffmpeg -ss 00:01:00 -i input.mp4 -to 00:02:30 -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k output.mp4
```

CRF 18 is recommended for trimming — clips are typically short segments the user
specifically selected, so higher quality is worth the modest file size increase.

**Trim last N seconds (requires knowing duration):**
```bash
# Get duration first
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4

# Then: duration - N = start time
ffmpeg -ss <start> -i input.mp4 -c copy output.mp4
```

**Remove first 10 seconds:**
```bash
ffmpeg -ss 10 -i input.mp4 -c copy output.mp4
```

## Under the Hood

ffmpeg operates in a demux → decode → filter → encode → mux pipeline. Where `-ss` falls in that pipeline determines behavior:

- **Before `-i`**: The demuxer seeks. Most container formats store keyframe positions in an index (the `moov` atom in MP4, or `cues` in MKV). ffmpeg jumps to the nearest indexed keyframe before the target. No decoding happens for the skipped portion. This can be off by up to the keyframe interval (often 2–5 seconds in broadcast content, up to 10s in some recordings).

- **After `-i`**: The demuxer reads from the beginning. The decoder decodes every frame. The filtergraph or encoder discards frames until the seek point is reached. Accurate to a single frame, but proportionally slow — trimming 1 second from a 2-hour file requires decoding 2 hours.

- **Combined (`-ss` before + re-encode)**: Demuxer jumps to nearest keyframe (fast). Decoder starts from that keyframe. Encoder begins writing output only at the exact requested frame. The few frames between the keyframe and the seek point are decoded and silently discarded. Output is frame-accurate.

`-avoid_negative_ts make_zero`: When the nearest keyframe is slightly before the requested start, timestamps on the copied packets can be negative. This flag shifts all timestamps up so the first packet is at 0, preventing playback issues.

## Sources

- Mux — "How to Extract Clips from Videos Using FFmpeg": https://www.mux.com/articles/clip-sections-of-a-video-with-ffmpeg
- OTTVerse — "How to Cut Video Using FFmpeg": https://ottverse.com/trim-cut-video-using-start-endtime-reencoding-ffmpeg/
- Shotstack — "How to Trim a Video Using FFmpeg": https://shotstack.io/learn/use-ffmpeg-to-trim-video/
- Bannerbear — "How to Trim a Video Using FFmpeg": https://www.bannerbear.com/blog/how-to-trim-a-video-using-ffmpeg/

## Learned from Usage

- Always use `-ss` before `-i` unless you specifically need sub-keyframe accuracy AND are okay with slow performance.
- When using `-c copy`, always add `-avoid_negative_ts make_zero` — prevents silent corruption in some players.
- `-to` behavior changes depending on whether `-ss` is before or after `-i`. When `-ss` is before `-i`, `-to` is a source timestamp. When `-ss` is after `-i`, `-to` is an output timestamp. Test with short clips when unsure.
- H.264 default keyframe interval in most encoders is 2 seconds (every 48–60 frames at 24–30fps). Expect up to 2 seconds of drift with stream copy seeking.
- For web video (MP4/HLS), always re-encode after trimming to ensure a keyframe at frame 0 — otherwise some players will show a black frame at the start.
