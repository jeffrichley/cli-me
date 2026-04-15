# Fake Live Streaming

## When to Use

Use fake live streaming when you need to broadcast pre-recorded content as if it were a live stream. Common use cases:

- **Scheduled content:** Streaming a pre-produced video at a specific time on YouTube Live, Twitch, or Facebook Live without being physically present
- **Looping background streams:** Running a 24/7 channel that loops music videos, ambient content, or tutorials
- **Testing live streaming infrastructure:** Validating encoder settings, CDN ingest, or player behavior without a real camera
- **Filling scheduled slots:** Airing sponsor content or evergreen material during downtime between actual live broadcasts

The key difference from regular file transcoding is the `-re` flag, which paces output to real-time. Without it, ffmpeg encodes as fast as possible and floods the RTMP server with data faster than real-time, causing the platform to drop frames, reject the stream, or disconnect.

## Technique

**`-re` (real-time pacing):** This flag throttles ffmpeg's read speed to match the stream's native frame rate. It must be placed immediately before the `-i` flag it applies to. If placed after `-i`, it has no effect. Specifically, `-re` reads input at the native frame rate, inserting sleeps between reads as needed.

**`-stream_loop -1` (infinite loop):** Causes ffmpeg to loop the input file indefinitely. The value `-1` means infinite; `N` would loop N additional times after the first play. Warning: `-stream_loop` may produce timestamp discontinuities at the loop point. Some platforms reject streams with timestamp jumps; some players show a seek artifact. For reliable looping, the concat demuxer approach is better.

**Concat demuxer for reliable looping:** Create a text playlist file listing the input file as many times as needed (or use a shell loop to generate it). The concat demuxer handles timestamps correctly across file boundaries, which avoids the discontinuity problem. This is the recommended approach for 24/7 streams.

**`-tune zerolatency`:** Sets x264 parameters to minimize encoder buffering and lookahead, reducing end-to-end latency. For fake live where latency does not matter (pre-recorded content), it still helps prevent encoder buffer buildup that can cause the stream to fall behind real-time.

**Shell restart loop:** RTMP connections can drop due to network issues, platform restarts, or stream key expiry. A shell `while true` loop around the ffmpeg command restarts it automatically when the process exits. A short `sleep` between restarts prevents hammering the platform's ingest server if it is rejecting connections.

**Timestamp handling:** Pre-recorded files have timestamps starting at 0 (or close to it). When streaming live, platforms expect monotonically increasing timestamps from stream start. ffmpeg handles this automatically when streaming from a single file. With loops or concat, timestamps must not reset — the concat demuxer handles this correctly.

## CLI Commands

### Single file to YouTube Live (one-shot, no loop)

```bash
ffmpeg \
  -re \
  -i input.mp4 \
  -c:v libx264 \
  -profile:v high \
  -level:v 4.1 \
  -preset veryfast \
  -tune zerolatency \
  -b:v 4500k \
  -maxrate 4500k \
  -bufsize 9000k \
  -g 60 \
  -keyint_min 60 \
  -sc_threshold 0 \
  -c:a aac \
  -b:a 160k \
  -ar 48000 \
  -ac 2 \
  -f flv \
  rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
```

### Infinite loop of a single file with `-stream_loop` (simpler but may have timestamp issues)

```bash
ffmpeg \
  -re \
  -stream_loop -1 \
  -i input.mp4 \
  -c:v libx264 \
  -profile:v high \
  -level:v 4.1 \
  -preset veryfast \
  -tune zerolatency \
  -b:v 4500k \
  -maxrate 4500k \
  -bufsize 9000k \
  -g 60 \
  -keyint_min 60 \
  -sc_threshold 0 \
  -c:a aac \
  -b:a 160k \
  -ar 48000 \
  -ac 2 \
  -f flv \
  rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
```

### Infinite loop using the concat demuxer (recommended — correct timestamps)

First, create a playlist file. For looping a single file, list it multiple times or use a large repeat count:

```bash
# Generate a playlist that loops the file 9999 times
python3 -c "
lines = ['ffconcat version 1.0']
for _ in range(9999):
    lines.append('file /absolute/path/to/input.mp4')
print('\n'.join(lines))
" > playlist.txt
```

Or create manually:
```
ffconcat version 1.0
file /absolute/path/to/input.mp4
file /absolute/path/to/input.mp4
file /absolute/path/to/input.mp4
```

Then stream using the concat demuxer:

```bash
ffmpeg \
  -re \
  -f concat \
  -safe 0 \
  -i playlist.txt \
  -c:v libx264 \
  -profile:v high \
  -level:v 4.1 \
  -preset veryfast \
  -tune zerolatency \
  -b:v 4500k \
  -maxrate 4500k \
  -bufsize 9000k \
  -g 60 \
  -keyint_min 60 \
  -sc_threshold 0 \
  -c:a aac \
  -b:a 160k \
  -ar 48000 \
  -ac 2 \
  -f flv \
  rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
```

`-safe 0` is required when the playlist contains absolute paths. Without it, ffmpeg rejects paths outside the playlist's directory.

### Shell restart loop for auto-reconnect on disconnect

Wrap the ffmpeg command in a `while true` loop with a short sleep between retries:

```bash
#!/bin/bash

STREAM_KEY="YOUR_STREAM_KEY"
RTMP_URL="rtmp://a.rtmp.youtube.com/live2/${STREAM_KEY}"
INPUT_FILE="/absolute/path/to/input.mp4"

while true; do
  echo "Starting stream at $(date)"
  ffmpeg \
    -re \
    -stream_loop -1 \
    -i "${INPUT_FILE}" \
    -c:v libx264 \
    -profile:v high \
    -level:v 4.1 \
    -preset veryfast \
    -tune zerolatency \
    -b:v 4500k \
    -maxrate 4500k \
    -bufsize 9000k \
    -g 60 \
    -keyint_min 60 \
    -sc_threshold 0 \
    -c:a aac \
    -b:a 160k \
    -ar 48000 \
    -ac 2 \
    -f flv \
    "${RTMP_URL}"
  EXIT_CODE=$?
  echo "ffmpeg exited with code ${EXIT_CODE} at $(date)"
  echo "Restarting in 5 seconds..."
  sleep 5
done
```

Save as `stream.sh`, run with `chmod +x stream.sh && ./stream.sh`. Run in a `tmux` or `screen` session to keep it alive after SSH disconnect.

### Concat playlist of multiple different files (playlist-style broadcast)

```bash
# playlist.txt
ffconcat version 1.0
file /media/videos/intro.mp4
file /media/videos/episode_01.mp4
file /media/videos/interstitial.mp4
file /media/videos/episode_02.mp4
file /media/videos/outro.mp4
```

```bash
ffmpeg \
  -re \
  -f concat \
  -safe 0 \
  -i /media/playlist.txt \
  -c:v libx264 \
  -profile:v high \
  -level:v 4.1 \
  -preset veryfast \
  -tune zerolatency \
  -b:v 4500k \
  -maxrate 4500k \
  -bufsize 9000k \
  -g 60 \
  -keyint_min 60 \
  -sc_threshold 0 \
  -c:a aac \
  -b:a 160k \
  -ar 48000 \
  -ac 2 \
  -f flv \
  rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
```

### Copy-mode relay (source already encoded, just re-pace and forward)

When the source file is already encoded to the correct spec, skip re-encoding with `-c copy`. This is CPU-minimal but the stream must already match the platform's requirements.

```bash
ffmpeg \
  -re \
  -stream_loop -1 \
  -i already_encoded_for_youtube.mp4 \
  -c copy \
  -f flv \
  rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
```

Warning: with `-c copy`, the `-tune zerolatency` and bitrate flags have no effect and should be omitted to avoid confusion.

## Under the Hood

**`-re` mechanics:** Without `-re`, ffmpeg reads and processes input as fast as the CPU allows — potentially 50-200x real-time for simple files on fast hardware. The RTMP server (YouTube, Twitch) receives this data burst and typically rejects or drops it because the platform's ingest pipeline is designed for real-time input. `-re` inserts `usleep()` calls between frame reads to match the input's declared frame rate. For a 30fps file, ffmpeg reads one frame, then sleeps ~33ms before the next.

**`-stream_loop` timestamp handling:** When ffmpeg loops using `-stream_loop`, it adds the duration of the previous play-through to the timestamps of the looped content. This means timestamps increase monotonically across loops in theory. In practice, container-level duration information is sometimes inaccurate (off by one frame, missing duration tag), which causes small jumps or gaps. These manifest as momentary video freezes or audio pops at the loop point. The concat demuxer recomputes timestamps based on actual decoded frame timing, which is more accurate.

**Concat demuxer vs `-stream_loop`:** The concat demuxer (`-f concat -i playlist.txt`) is a full demuxer that reads multiple input files sequentially and presents them as a single continuous stream. It handles timestamp normalization explicitly: each file's timestamps are offset by the cumulative duration of all previous files. This is the standard solution for multi-file playlists and is used by tools like ffplayout and owncast.

**`-safe 0`:** The concat demuxer's security model by default rejects absolute paths and `..` components in playlist file entries to prevent directory traversal attacks when playlist files come from untrusted sources. For local use, `-safe 0` disables this check.

**Why `-tune zerolatency` matters even for pre-recorded content:** x264's default lookahead buffer (`rc-lookahead=40`) means the encoder looks 40 frames ahead when making rate control decisions. This adds ~1.3 seconds of latency at 30fps. For a streaming output, this means ffmpeg is encoding at real-time but the encoded packets may be up to 1.3 seconds behind the input position. Combined with network buffering, this can cause the stream to fall behind real-time and eventually disconnect. `-tune zerolatency` sets `rc-lookahead=0`, eliminating this accumulating lag.

**`-bufsize` and real-time streaming:** The VBV buffer size controls how much the encoder can vary its bitrate over time. For live streaming, a `bufsize` equal to `2× maxrate` means a 2-second smoothing window. Larger bufsize allows more quality variation but means the encoder may temporarily exceed the instantaneous bitrate, which can cause the RTMP connection to be throttled or dropped by platforms that enforce strict bitrate limits. Twitch, in particular, enforces a 6000k hard cap at the ingest level.

## Sources

- [Mux Blog: How to Fake a Live Stream with FFmpeg](https://mux.com/blog/how-to-fake-a-live-stream/)
- [LiveReacting: Loop Video with FFmpeg for Live Streaming](https://livereacting.com/blog/loop-video-ffmpeg-live-stream/)
- [ConsultWithGriff: 24/7 Livestreaming with FFmpeg](https://consultwithgriff.com/24-7-livestreaming-with-ffmpeg/)
- [FFmpeg concat Demuxer Documentation](https://ffmpeg.org/ffmpeg-formats.html#concat-1)

## Learned from Usage

- `-re` must come before `-i`. Writing `ffmpeg -i input.mp4 -re ...` causes the real-time pacing to not take effect and ffmpeg floods the RTMP server at encode speed.
- YouTube disconnects streams that stop receiving data for more than ~30 seconds. If your file ends and there is no loop or restart, YouTube marks the stream as ended. You cannot resume the same stream key for several minutes. Always use a loop or restart script for scheduled streams.
- When using the restart loop script, test it with a short file and simulate a disconnect (Ctrl+C the ffmpeg process while the loop is running) to verify the restart behavior works before the actual broadcast.
- The concat demuxer requires all files in the playlist to have the same codec, resolution, frame rate, and sample rate. If your playlist mixes source files with different specs, add a scale/fps/aresample filter chain before the encoder to normalize them. Alternatively, pre-process all source files to a common spec before building the playlist.
- On Linux servers without a display, ffmpeg may emit warnings about missing display or video device. These are harmless for headless streaming — suppress with `-loglevel warning` if they clutter logs.
- Platform stream keys can expire or be rotated. If the restart loop reconnects but gets immediate RTMP rejection (not a network error), the stream key has likely expired. Check the platform dashboard.
- `tmux new -s stream` then detach with `Ctrl+B D` is the standard way to run a streaming session that survives SSH disconnects on a remote server.
