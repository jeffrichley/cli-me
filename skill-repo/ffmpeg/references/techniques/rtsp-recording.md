# RTSP Recording

## When to Use

Use this technique when recording a live RTSP stream to disk — security cameras, IP cameras, CCTV systems, or any device that exposes an `rtsp://` endpoint. The key goals are: reliable reception without packet loss, crash-resilient output files, predictable segment filenames for downstream processing, and automatic restart if the connection drops.

Use MKV segments for reliability. Use MP4 only when downstream tooling requires it and the camera connection is stable. Use systemd (Linux) or a shell restart loop for production deployments where the process must survive reboots and network interruptions.

## Technique

### Always Use TCP Transport

RTSP over UDP is the protocol default, but UDP is unreliable on networks with packet loss or firewall interference. Lost UDP packets produce visual artifacts, audio glitches, and broken keyframes in the output file. Always set `-rtsp_transport tcp` unless you have a specific reason not to (e.g., a camera that refuses TCP). TCP adds a small latency overhead but makes the stream reliable.

### Wall Clock Timestamps

IP cameras often have incorrect or drifting internal clocks. Without `-use_wallclock_as_timestamps 1`, ffmpeg uses the timestamps embedded in the RTP stream, which can cause audio/video sync issues or segment boundary misalignment. Setting this flag makes ffmpeg use the system wall clock instead, which is consistent and accurate.

### Segmented Recording with -f segment

The `segment` muxer writes a series of output files instead of one continuous file. Key options:

- `-segment_time 900` — close and start a new file every 900 seconds (15 minutes). Adjust to taste.
- `-strftime 1` — enables strftime format codes in the output filename pattern, so `%Y-%m-%d_%H-%M-%S` expands to a timestamp like `2024-03-15_14-30-00`.
- `-segment_atclocktime 1` — aligns segment boundaries to even multiples of `segment_time` on the wall clock. For example, with `segment_time 900`, segments always start at :00, :15, :30, :45 on the hour regardless of when recording started. This is useful for predictable archival and searching.
- `-reset_timestamps 1` — resets the timestamp counter at each segment boundary, so each file starts at time 0 rather than inheriting the running stream timestamp.

### MKV vs MP4 for Crash Resilience

MP4 stores its index (the `moov` atom) at the end of the file by default. If ffmpeg is killed or crashes, the moov atom is never written and the file is unplayable (or requires recovery tools). MKV writes index data incrementally as it records, so a crash produces a truncated but playable file. For always-on recording where crashes are possible, MKV is strongly preferred. If MP4 is required, use `-movflags +frag_keyframe+empty_moov` to write a fragmented MP4 with incremental atoms.

### Automatic Restart

An RTSP stream can drop due to camera reboot, network interruption, or ffmpeg error. For production recording, the process must restart automatically. On Linux, a systemd service with `Restart=always` and `RestartSec=5` is the right tool. A shell `while true` loop with a sleep is an acceptable alternative for simple deployments.

## CLI Commands

**Basic recording — 15-minute MKV segments with timestamp filenames:**
```bash
ffmpeg -rtsp_transport tcp \
  -use_wallclock_as_timestamps 1 \
  -i "rtsp://user:pass@camera-ip:554/stream" \
  -c copy \
  -f segment \
  -segment_time 900 \
  -segment_atclocktime 1 \
  -strftime 1 \
  -reset_timestamps 1 \
  "recordings/cam1_%Y-%m-%d_%H-%M-%S.mkv"
```

**5-minute MP4 segments (fragmented for crash resilience):**
```bash
ffmpeg -rtsp_transport tcp \
  -use_wallclock_as_timestamps 1 \
  -i "rtsp://user:pass@camera-ip:554/stream" \
  -c copy \
  -f segment \
  -segment_time 300 \
  -strftime 1 \
  -reset_timestamps 1 \
  -movflags +frag_keyframe+empty_moov \
  "recordings/cam1_%Y-%m-%d_%H-%M-%S.mp4"
```

**With error logging to file:**
```bash
ffmpeg -rtsp_transport tcp \
  -use_wallclock_as_timestamps 1 \
  -i "rtsp://user:pass@camera-ip:554/stream" \
  -c copy \
  -f segment \
  -segment_time 900 \
  -segment_atclocktime 1 \
  -strftime 1 \
  -reset_timestamps 1 \
  "recordings/cam1_%Y-%m-%d_%H-%M-%S.mkv" \
  2>> "recordings/cam1_errors.log"
```

**Systemd service unit (auto-restart on failure or reboot):**
```ini
# /etc/systemd/system/camera-record-cam1.service
[Unit]
Description=RTSP recording — Camera 1
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=recorder
WorkingDirectory=/var/recordings
ExecStartPre=/bin/mkdir -p /var/recordings/cam1
ExecStart=/usr/bin/ffmpeg \
  -rtsp_transport tcp \
  -use_wallclock_as_timestamps 1 \
  -i rtsp://user:pass@camera-ip:554/stream \
  -c copy \
  -f segment \
  -segment_time 900 \
  -segment_atclocktime 1 \
  -strftime 1 \
  -reset_timestamps 1 \
  /var/recordings/cam1/cam1_%%Y-%%m-%%d_%%H-%%M-%%S.mkv
Restart=always
RestartSec=5
StandardError=append:/var/log/camera-record-cam1.log

[Install]
WantedBy=multi-user.target
```

Enable and start with:
```bash
sudo systemctl daemon-reload
sudo systemctl enable camera-record-cam1
sudo systemctl start camera-record-cam1
```

**Shell restart loop (simpler alternative to systemd):**
```bash
#!/bin/bash
mkdir -p recordings
while true; do
  echo "$(date): Starting RTSP recording..." >> recordings/cam1.log
  ffmpeg -rtsp_transport tcp \
    -use_wallclock_as_timestamps 1 \
    -i "rtsp://user:pass@camera-ip:554/stream" \
    -c copy \
    -f segment \
    -segment_time 900 \
    -segment_atclocktime 1 \
    -strftime 1 \
    -reset_timestamps 1 \
    "recordings/cam1_%Y-%m-%d_%H-%M-%S.mkv" \
    2>> recordings/cam1.log
  echo "$(date): ffmpeg exited ($?), restarting in 5s..." >> recordings/cam1.log
  sleep 5
done
```

## Under the Hood

RTSP (Real Time Streaming Protocol) is a control protocol — it negotiates the media session but does not carry the media itself. The actual audio and video data is carried by RTP (Real-time Transport Protocol) over UDP or TCP. When using TCP, RTP packets are interleaved inside the RTSP TCP connection, which means the OS TCP stack handles retransmission of lost packets, making the stream reliable at the cost of slightly increased latency.

The `-use_wallclock_as_timestamps 1` option overrides the PTS (presentation timestamp) values from the incoming RTP stream with the actual wall clock time at the moment each packet is received. This corrects drift and jitter from cameras with poor internal clocks. The side effect is that if the network introduces variable latency (jitter), that jitter is stamped into the recording — but for surveillance use cases this is almost always preferable to a stream with inconsistent segment lengths.

The `segment` muxer's `-segment_atclocktime 1` feature works by computing `floor(current_time / segment_time) * segment_time` to determine the next boundary, then triggering a segment close at that exact wall clock second. This requires that segments are configured to reset timestamps (`-reset_timestamps 1`) or the PTS continuity check may reject the boundary.

In systemd unit files, `%` characters must be escaped as `%%` because systemd uses `%` as its own specifier prefix.

## Sources

- Tom Humph — "Recording RTSP Streams with FFmpeg" (Medium): https://medium.com/@tomhumphrey/recording-rtsp-streams-with-ffmpeg
- cavelab.dev — "FFmpeg RTSP stream recording": https://cavelab.dev/wiki/FFmpeg_RTSP_recording
- FFmpeg official docs — RTSP: https://ffmpeg.org/ffmpeg-protocols.html#rtsp
- FFmpeg official docs — segment muxer: https://ffmpeg.org/ffmpeg-formats.html#segment_002c-stream_005fsegment_002c-ssegment

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
