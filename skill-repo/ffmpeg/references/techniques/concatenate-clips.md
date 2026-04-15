# Concatenate Clips

## When to Use

Use the **concat demuxer** when all clips share the same codec, resolution, framerate, and audio configuration. It is instant and lossless — no re-encode occurs.

Use the **concat filter** when clips differ in codec, resolution, framerate, or when one or more clips are missing audio. This always re-encodes.

Do not confuse the two — the demuxer is invoked with `-f concat -i filelist.txt`, while the filter is invoked inside `-filter_complex` using `[v][a]concat=`. Using the wrong one for the wrong situation is the most common source of concat bugs.

The **TS intermediate method** (encode each clip to MPEG-TS, then `cat` together) is legacy. Avoid it unless you are working around a bug in very old FFmpeg builds.

## Technique

**Concat demuxer (lossless, same codec/resolution/fps):**

1. Write a plain-text `filelist.txt` where each line is `file '/absolute/or/relative/path.mp4'`.
2. Run: `ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4`
3. `-safe 0` is required when paths are absolute or contain special characters.
4. If you see `DTS ... out of order` or `non monotonous DTS` errors, add `-fflags +genpts` before the output to regenerate timestamps.

**Concat filter (re-encode, handles mismatched clips):**

- Connect inputs via the filtergraph: `[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]`
- `n=` is the number of segments. `v=1:a=1` means one video stream and one audio stream out.
- Map the named outputs: `-map [v] -map [a]`
- You must specify output codec and quality explicitly since this is a re-encode.

**Missing audio on one clip:**

Add a silent audio stream with `anullsrc` for the clip that has no audio before concatenating:

```
anullsrc=channel_layout=stereo:sample_rate=44100[silence];
[0:v][0:a][1:v][silence]concat=n=2:v=1:a=1[v][a]
```

Match `channel_layout` and `sample_rate` to your other clips.

## CLI Commands

**Demuxer — lossless concat:**
```bash
# filelist.txt contents:
# file '/path/to/clip1.mp4'
# file '/path/to/clip2.mp4'
# file '/path/to/clip3.mp4'

ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4
```

**Demuxer — with timestamp regeneration (fixes DTS ordering errors):**
```bash
ffmpeg -f concat -safe 0 -i filelist.txt -c copy -fflags +genpts output.mp4
```

**Filter — concat mismatched clips (re-encode):**
```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -crf 18 -c:a aac -b:a 192k \
  output.mp4
```

**Filter — add silent audio to a video-only clip before concat:**
```bash
ffmpeg -i clip1.mp4 -i clip2_no_audio.mp4 \
  -filter_complex \
    "aevalsrc=0:channel_layout=stereo:sample_rate=44100:duration=5[silence];
     [0:v][0:a][1:v][silence]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -crf 18 -c:a aac -b:a 192k \
  output.mp4
```

Or using `anullsrc` with `-shortest` (required — `anullsrc` generates infinite silence):
```bash
ffmpeg -i clip1.mp4 -i clip2_no_audio.mp4 \
  -filter_complex \
    "anullsrc=channel_layout=stereo:sample_rate=44100[silence];
     [0:v][0:a][1:v][silence]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -crf 18 -c:a aac -b:a 192k \
  -shortest \
  output.mp4
```

**Warning:** Without `-shortest`, `anullsrc` produces an unbounded output that corrupts the MP4. Always include `-shortest` when using `anullsrc`.

**TS intermediate method (legacy — avoid):**
```bash
ffmpeg -i clip1.mp4 -c copy clip1.ts
ffmpeg -i clip2.mp4 -c copy clip2.ts
ffmpeg -i "concat:clip1.ts|clip2.ts" -c copy output.mp4
```

## Under the Hood

The **concat demuxer** reads packets directly from each file in sequence and feeds them to the muxer with adjusted timestamps. No decoding or encoding occurs. This is why all streams must be compatible — the muxer receives raw packets and has no opportunity to convert them.

The **concat filter** is a real-time filter that decodes all inputs, processes frames in sequence, and re-encodes. It handles format mismatches because it operates on decoded frames, not encoded packets. The `n=` parameter tells it how many segment inputs to expect; `v=` and `a=` control the number of output video and audio streams.

`-fflags +genpts` tells FFmpeg to generate new presentation timestamps from the DTS (decode timestamp) rather than trusting the timestamps in the source packets. This fixes issues that arise when demuxed files have slightly inconsistent or overlapping timestamps.

## Sources

- WaveSpeedAI — "How to Merge and Concatenate Videos with FFmpeg": https://wavespeed.ai/blog/posts/blog-how-to-merge-concatenate-videos-ffmpeg/
- Shotstack — "FFmpeg Concat: How to Merge Videos": https://shotstack.io/learn/use-ffmpeg-to-concatenate-video/
- OTTVerse — "How to Concatenate MP4 Files Using FFmpeg in 3 Different Ways": https://ottverse.com/3-easy-ways-to-concatenate-mp4-files-using-ffmpeg/
- Gumlet — "How to Combine Videos Using FFmpeg Concat": https://www.gumlet.com/learn/ffmpeg-concat/

## Learned from Usage

- The most common concat mistake: using `-f concat` with clips that have different resolutions or codecs. FFmpeg will not error clearly — the output will be corrupted or truncated.
- Always use absolute paths in `filelist.txt` when running from scripts to avoid `-safe 0` surprises.
- On Windows with Git Bash, `/tmp` paths in `filelist.txt` are not resolved by ffmpeg — use the actual Windows path (e.g., `C:/Users/name/AppData/Local/Temp/clip.mp4`). ffmpeg reads `filelist.txt` natively; Git Bash path translation does not apply to file contents.
- Non-monotonic DTS warnings (`Non-monotonic DTS; previous: X, current: Y`) are common when concatenating clips made by the same encoder due to slight AAC timestamp rounding. These are benign for normal playback; add `-fflags +genpts` if strict timestamp compliance is required.
- When the concat filter produces audio sync drift, verify that all input clips have the same sample rate before concatenating.
- Three or more clips: increment `n=` and extend the input chain — `[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1`.
