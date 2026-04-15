# Extract Audio

## When to Use

Use when you need to pull the audio track(s) out of a video file — for transcription, archiving, remixing, distribution as a podcast, or simply converting between audio formats. Also useful for inspecting what audio tracks exist in a multi-track file.

## Technique

**`-vn` flag:** Disables video output. Without it, ffmpeg would try to include the video stream and fail or produce an unexpected output container.

**Stream copy (`-c:a copy`):** Copies the audio bitstream without re-encoding. This is the fastest option and perfectly lossless — use it whenever the source codec matches what the output container accepts. No quality loss, no CPU cost.

**When you must re-encode:**
- Source codec is not supported by the target container (e.g., AC-3 in an MP3 file)
- You want to change the format (e.g., AAC → MP3)
- You need to control bitrate or quality

**MP3 encoding:**
- VBR: `-q:a 2` — Variable Bitrate, quality scale 0 (best) to 9 (worst). Quality 2 targets ~190 kbps, effectively transparent to most listeners.
- CBR: `-b:a 192k` — Constant Bitrate. Predictable file size, slightly less efficient than VBR.

**AAC encoding:**
- AAC at 128k is roughly equivalent in perceived quality to MP3 at 192k due to a more efficient codec.
- Use `-c:a aac -b:a 128k` for broad compatibility (native ffmpeg encoder).
- Use `-c:a libfdk_aac -b:a 128k` for higher quality if your ffmpeg build includes it (requires separate compilation).

**WAV export (uncompressed):**
- PCM 16-bit: `-c:a pcm_s16le` — standard CD quality, widest compatibility
- PCM 24-bit: `-c:a pcm_s24le` — studio quality, used in DAW workflows
- The `le` suffix = little-endian (correct for all modern platforms)

**Multi-track selection with `-map`:**
- `-map 0:a` — all audio streams
- `-map 0:a:0` — first audio stream (default behavior)
- `-map 0:a:1` — second audio stream (e.g., director's commentary, alternate language)
- Combine with `-map_metadata 0` to copy stream metadata

**Inspect tracks before extracting:**
```bash
ffprobe -v error -show_streams -select_streams a input.mkv
```

## CLI Commands

**Copy audio as-is (fastest, lossless):**
```bash
ffmpeg -i input.mp4 -vn -c:a copy output.aac
```
Extension must match the codec — `.aac` for AAC, `.ac3` for Dolby, `.opus` for Opus, etc.

**Extract to MP3 (VBR, high quality):**
```bash
ffmpeg -i input.mp4 -vn -c:a libmp3lame -q:a 2 output.mp3
```

**Extract to MP3 (CBR 192k):**
```bash
ffmpeg -i input.mp4 -vn -c:a libmp3lame -b:a 192k output.mp3
```

**Extract to AAC 128k:**
```bash
ffmpeg -i input.mp4 -vn -c:a aac -b:a 128k output.m4a
```

**Extract to WAV (16-bit PCM):**
```bash
ffmpeg -i input.mp4 -vn -c:a pcm_s16le output.wav
```

**Extract to WAV (24-bit PCM for studio use):**
```bash
ffmpeg -i input.mp4 -vn -c:a pcm_s24le output.wav
```

**Extract a specific audio track (second track):**
```bash
ffmpeg -i input.mkv -map 0:a:1 -vn -c:a copy output.aac
```

**Extract all audio tracks as separate files:**
```bash
ffmpeg -i input.mkv -map 0:a:0 -c:a copy track0.aac -map 0:a:1 -c:a copy track1.aac
```

**Extract with metadata preserved:**
```bash
ffmpeg -i input.mp4 -vn -c:a libmp3lame -q:a 2 -map_metadata 0 output.mp3
```

**Extract audio from a time range:**
```bash
ffmpeg -ss 00:01:00 -i input.mp4 -to 00:03:00 -vn -c:a copy output.aac
```

## Under the Hood

ffmpeg's stream selection without explicit `-map` follows automatic selection rules: it picks the "best" stream of each type. For audio that means the stream with the most channels, or the first audio stream if channel counts are equal.

The `-vn` flag tells ffmpeg to include zero video streams in the output. Without it, ffmpeg would include the video stream (if the container supports it) and likely error when the container (e.g., `.mp3`) does not accept video.

For **copy mode** (`-c:a copy`), ffmpeg reads compressed audio packets from the demuxer and writes them directly to the muxer with no modification. The codec parser still runs to validate packet boundaries, but no decode/encode cycle occurs. This means no quality degradation and near-zero CPU usage — it runs at I/O speed.

For **re-encode mode**, the pipeline is: demux → decode (to PCM) → encode (to target codec) → mux. Each encode introduces generation loss. For MP3 and AAC, a single transcode from a high-quality source is inaudible at typical bitrates; chained transcodes compound artifacts.

**Container vs codec:** The output container (determined by file extension) must support the codec. AAC fits in `.m4a`, `.mp4`, `.mov`, `.mkv`. MP3 fits in `.mp3` and `.mkv`. PCM fits in `.wav` and `.mkv`. If there is a mismatch, ffmpeg will error with "Could not find tag for codec".

## Sources

- Mux — "How to Extract Audio from Video Files Using FFmpeg": https://www.mux.com/articles/extract-audio-from-a-video-file-with-ffmpeg
- OTTVerse — "Extract Audio from Video Using FFmpeg": https://ottverse.com/extract-audio-from-video-using-ffmpeg/
- Cloudinary — "How to Use FFmpeg to Extract Audio From Video": https://cloudinary.com/guides/front-end-development/ffmpeg-extract-audio
- Baeldung — "Extracting Audio From Video Files Using FFmpeg": https://www.baeldung.com/linux/ffmpeg-audio-from-video

## Learned from Usage

- Always verify the codec in the source before using `-c:a copy`. `ffprobe -show_streams -select_streams a` shows codec_name. Copying AAC into an `.mp3` file will fail.
- `-q:a 2` for MP3 is the community-standard recommendation (from the LAME encoder docs). Don't go below 0 or above 5 for distribution-quality audio.
- When extracting a single track from a multi-track file with `-c:a copy`, always use `-map 0:a:N` explicitly — the automatic selection may not pick the track you expect.
- `.m4a` is the standard extension for AAC-in-MP4 audio files (Apple ecosystem compatible). `.aac` is a raw AAC bitstream without a container — both work, but `.m4a` is better for metadata and seeking.
- If extracting for speech transcription (Whisper, etc.), convert to WAV 16kHz mono: `ffmpeg -i input.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le output.wav`
