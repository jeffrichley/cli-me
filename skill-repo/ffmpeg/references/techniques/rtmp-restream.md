# RTMP Restreaming

## When to Use

Use RTMP restreaming when you need to simultaneously broadcast a live stream to multiple platforms (YouTube, Twitch, Facebook, etc.) without running separate encoder instances. The two primary patterns are:

- **Transcode + fan-out:** Your source (OBS, camera, encoder) sends one RTMP stream to ffmpeg. ffmpeg transcodes it and fans out to multiple platforms using the tee muxer. One encode pass, N destinations.
- **Relay (pass-through):** ffmpeg receives an RTMP stream and forwards it to multiple platforms using `-c copy`. No re-encoding. Use when your source is already encoded to the correct spec and you just need to fan out.
- **Receive mode (`-listen 1`):** ffmpeg acts as an RTMP server, accepting inbound connections from OBS or another encoder. Combined with the tee muxer, this is a complete self-hosted restreaming server in a single command.

Avoid this pattern when platforms require different resolutions or bitrates per destination — in that case you need multi-bitrate output with per-destination transcodes, which multiplies CPU cost.

## Technique

**The tee muxer** (`-f tee`) sends a single encoded stream to multiple outputs, identified by `|`-separated URLs in the output argument. Each URL can have per-output options in `[key=value:key=value]` brackets before it.

Critical: `-map 0` is required when using the tee muxer. Without it, ffmpeg may select only one stream (typically video) and the audio will be silently dropped. Always explicitly map all streams you want to send.

**`[f=flv:onfail=ignore]`:** The `f=flv` sets the container format per-output (RTMP requires FLV). The `onfail=ignore` option tells ffmpeg to continue if one destination fails or disconnects. Without this, a single failed destination (e.g., Twitch goes down) stops the entire stream to all platforms.

**`-listen 1`:** Placed before the `-i` URL, this switches ffmpeg from RTMP client mode (connecting to a server) to RTMP server mode (listening for incoming connections). OBS points its RTMP output at `rtmp://your-server:1935/live/streamkey`. ffmpeg accepts the connection and processes it.

**Platform RTMP URL formats:**

| Platform  | URL format                                              | Notes                        |
|-----------|---------------------------------------------------------|------------------------------|
| YouTube   | `rtmp://a.rtmp.youtube.com/live2/STREAM_KEY`            | Primary ingest               |
| YouTube   | `rtmp://b.rtmp.youtube.com/live2/STREAM_KEY`            | Backup ingest                |
| Twitch    | `rtmp://live.twitch.tv/app/STREAM_KEY`                  | Use nearest ingest server    |
| Twitch    | `rtmp://live-ams.twitch.tv/app/STREAM_KEY`              | Example: Amsterdam           |
| Facebook  | `rtmps://live-api-s.facebook.com:443/rtmp/STREAM_KEY`   | RTMPS (TLS), not plain RTMP  |
| LinkedIn  | `rtmps://videos.linkedin.com:443/live-api/STREAM_KEY`   | RTMPS required               |

Facebook and LinkedIn require RTMPS (RTMP over TLS). ffmpeg supports this natively — just use `rtmps://` in the URL.

**Encoding settings for multi-platform live:** Most platforms accept H.264 Baseline/Main at up to 6000k, AAC-LC at 128-320k, 1080p30 max. YouTube additionally accepts 1080p60. Twitch limits: 6000k video, 160k audio, 1080p60. Keep presets fast (`-preset veryfast` or `ultrafast`) to ensure real-time encoding.

## CLI Commands

### Transcode + tee to 3 platforms (YouTube, Twitch, Facebook)

```bash
ffmpeg \
  -i rtmp://localhost:1935/live/input_key \
  -c:v libx264 \
  -profile:v main \
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
  -map 0 \
  -f tee \
  "[f=flv:onfail=ignore]rtmp://a.rtmp.youtube.com/live2/YOUR_YOUTUBE_KEY|[f=flv:onfail=ignore]rtmp://live.twitch.tv/app/YOUR_TWITCH_KEY|[f=flv:onfail=ignore]rtmps://live-api-s.facebook.com:443/rtmp/YOUR_FACEBOOK_KEY"
```

### Listen mode: receive from OBS, relay to 2 platforms with copy (no re-encode)

```bash
ffmpeg \
  -listen 1 \
  -i rtmp://0.0.0.0:1935/live/stream \
  -c copy \
  -map 0 \
  -f tee \
  "[f=flv:onfail=ignore]rtmp://a.rtmp.youtube.com/live2/YOUR_YOUTUBE_KEY|[f=flv:onfail=ignore]rtmp://live.twitch.tv/app/YOUR_TWITCH_KEY"
```

OBS stream settings: Server = `rtmp://YOUR_SERVER_IP:1935/live`, Stream key = `stream`.

### Listen mode: receive from OBS, transcode + fan-out to 3 platforms

```bash
ffmpeg \
  -listen 1 \
  -i rtmp://0.0.0.0:1935/live/obs_input \
  -c:v libx264 \
  -profile:v main \
  -level:v 4.1 \
  -preset veryfast \
  -tune zerolatency \
  -b:v 4000k \
  -maxrate 4000k \
  -bufsize 8000k \
  -g 60 \
  -keyint_min 60 \
  -sc_threshold 0 \
  -c:a aac \
  -b:a 160k \
  -ar 48000 \
  -ac 2 \
  -map 0:v \
  -map 0:a \
  -f tee \
  "[f=flv:onfail=ignore]rtmp://a.rtmp.youtube.com/live2/YOUTUBE_KEY|[f=flv:onfail=ignore]rtmp://live.twitch.tv/app/TWITCH_KEY|[f=flv:onfail=ignore]rtmps://live-api-s.facebook.com:443/rtmp/FACEBOOK_KEY"
```

### Multiple outputs WITHOUT tee (independent ffmpeg outputs — use when formats differ)

This approach uses ffmpeg's native multiple-output mode. Each output is a separate process thread. The source is decoded once, then each output is encoded independently. Useful when destinations need different codecs or bitrates.

```bash
ffmpeg \
  -i rtmp://localhost:1935/live/input \
  -c:v libx264 -profile:v high -level:v 4.1 -preset veryfast -b:v 5000k -maxrate 5000k -bufsize 10000k -g 60 -keyint_min 60 -sc_threshold 0 \
  -c:a aac -b:a 192k -ar 48000 \
  -map 0:v -map 0:a \
  -f flv rtmp://a.rtmp.youtube.com/live2/YOUTUBE_KEY \
  -c:v libx264 -profile:v main -level:v 4.0 -preset veryfast -b:v 2500k -maxrate 2500k -bufsize 5000k -g 60 -keyint_min 60 -sc_threshold 0 \
  -c:a aac -b:a 128k -ar 48000 \
  -map 0:v -map 0:a \
  -f flv rtmp://live.twitch.tv/app/TWITCH_KEY
```

Note: unlike the tee muxer, this re-runs the full video encode for each output. The source is still decoded once.

### Record locally while streaming to one platform

```bash
ffmpeg \
  -listen 1 \
  -i rtmp://0.0.0.0:1935/live/stream \
  -c:v libx264 -profile:v high -level:v 4.1 -preset veryfast -b:v 5000k -maxrate 5000k -bufsize 10000k -g 60 -keyint_min 60 -sc_threshold 0 \
  -c:a aac -b:a 192k -ar 48000 \
  -map 0 \
  -f tee \
  "[f=flv:onfail=ignore]rtmp://a.rtmp.youtube.com/live2/YOUTUBE_KEY|[f=mp4]local_recording.mp4"
```

The `[f=mp4]` tee output writes a local MP4 simultaneously. Note: the MP4 file will not be fully playable until ffmpeg exits cleanly (the `moov` atom is written on close). For crash-safe local recording, use `-f segment` or write a separate MKV.

## Under the Hood

**How the tee muxer works:** The tee muxer intercepts encoded packets (after the encoder, before any muxer) and writes each packet to every listed output independently. Each output has its own muxer instance (FLV, RTMP, etc.) and its own network connection. The tee muxer does not copy decoded frames — it copies encoded packets, so it is zero-overhead relative to a single output.

**`-map 0` with tee:** When using the tee muxer, ffmpeg's stream selection heuristics sometimes choose only one stream. `-map 0` explicitly selects all streams from input 0. Alternatively, `-map 0:v -map 0:a` selects the first video and first audio stream explicitly, which is cleaner when you have subtitle or data streams you don't want to forward.

**`onfail=ignore`:** Without this, if any tee output fails (network disconnect, RTMP connection refused, platform goes down), ffmpeg stops the entire encode and all other outputs stop as well. With `onfail=ignore`, the failed output is silently dropped and the other outputs continue. Always use this for multi-platform streaming.

**RTMP vs RTMPS:** Plain RTMP sends data unencrypted on port 1935. RTMPS is RTMP tunneled over TLS (like HTTPS), typically on port 443. Facebook and LinkedIn require RTMPS. ffmpeg handles both natively via the `rtmp://` and `rtmps://` URL schemes. No extra flags needed.

**`-listen 1`:** This flag enables ffmpeg's built-in RTMP server mode. ffmpeg binds to the specified address and port and waits for an incoming RTMP connection. It only accepts one connection at a time — it is not a full RTMP server like nginx-rtmp or SRS. For multi-stream ingest or web dashboard, use nginx-rtmp and have it call ffmpeg via `exec`.

**`-tune zerolatency`:** Sets several x264 parameters (`no-mbtree=1`, `sync-lookahead=0`, `rc-lookahead=0`, `sliced-threads=1`, `b-adapt=0`, `bframes=0`) that reduce encoder latency. The trade-off is slightly lower compression efficiency. For live streaming this is almost always the right call — viewers tolerate slightly lower quality more than they tolerate stutter from a backed-up encoder buffer.

**Keyframe interval for live:** Platforms typically require keyframes every 2 seconds. At 30fps, `-g 60 -keyint_min 60`; at 60fps, `-g 120 -keyint_min 120`. YouTube enforces this. Twitch recommends it. A longer GOP improves compression but makes the stream harder to join mid-stream and harder for the platform's transcoder to work with.

## Sources

- [Jonathan Hamberg: FFmpeg RTMP Restreaming Guide](https://jonathanhamberg.com/post/2019-10-27-ffmpeg-restream-multiple-services/)
- [ffplayout discussion: Tee Muxer for Multi-Platform Streaming](https://github.com/ffplayout/ffplayout/discussions/371)
- [ConsultWithGriff: Live Streaming with FFmpeg](https://consultwithgriff.com/streaming-with-ffmpeg/)
- [FFmpeg Tee Muxer Documentation](https://ffmpeg.org/ffmpeg-formats.html#tee-1)

## Learned from Usage

- Forgetting `-map 0` with the tee muxer drops audio silently. The stream appears to work but destinations receive video-only. Always add `-map 0` or explicit `-map 0:v -map 0:a`.
- The tee output string must be a single shell argument (quoted). The `|` separators are parsed by ffmpeg, not the shell. If you put them unquoted, the shell interprets `|` as a pipe operator and the command fails with a confusing error.
- Facebook changed from `rtmp://` to `rtmps://` in 2019. Old guides show the plain RTMP URL, which no longer works. Use `rtmps://live-api-s.facebook.com:443/rtmp/KEY`.
- When using `-listen 1`, ffmpeg blocks until a client connects. There is no timeout by default. If OBS disconnects and reconnects, ffmpeg does not re-enter listen mode — you must restart ffmpeg. Wrap it in a shell restart loop (see fake-live-stream.md) to handle reconnects.
- The per-output `[f=flv]` format specifier is required even though RTMP streams are almost always FLV. Without it, the tee muxer may choose the wrong format for some outputs.
- For crash-safe local recording alongside streaming, use `-f matroska` (MKV) instead of MP4 — MKV writes a valid index as it goes and is playable even if the process is killed mid-stream.
