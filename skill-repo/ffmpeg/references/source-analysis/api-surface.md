# ffmpeg API Surface

## Binaries

- **ffmpeg** — the encoder/decoder/filter/muxer. Does all media processing.
- **ffprobe** — the analyzer. Reads file metadata without processing.
- **ffplay** — media player (rarely used in automation)

## Input/Output Model

ffmpeg reads one or more inputs (`-i`), applies filters, and writes one or more outputs.

```
ffmpeg [global options] [input options] -i input [input options] -i input2 \
  [output options] output [output options] output2
```

## Key Flag Categories

### Codec Selection
- `-c:v libx264` / `-c:v libx265` / `-c:v libvpx-vp9` / `-c:v libsvtav1` — video encoder
- `-c:a aac` / `-c:a libmp3lame` / `-c:a libopus` / `-c:a libvorbis` — audio encoder
- `-c copy` — stream copy (no re-encode, fastest, lossless)
- `-c:v h264_nvenc` / `-c:v h264_vaapi` / `-c:v h264_videotoolbox` — hardware encoders

### Quality Control
- `-crf N` — constant rate factor (18=near-lossless, 23=default, 28=small)
- `-b:v Nk` — target video bitrate
- `-maxrate Nk` / `-bufsize Nk` — capped VBR
- `-q:v N` — quality scale (codec-specific)
- `-preset` — speed/quality tradeoff (ultrafast → veryslow)

### Filtering
- `-vf "filter1,filter2"` — simple video filter chain (single input)
- `-af "filter1,filter2"` — simple audio filter chain (single input)
- `-filter_complex "..."` — multi-input filtergraph with stream labels

### Container & Output
- `-f mp4` / `-f flv` / `-f hls` / `-f dash` / `-f segment` — output format
- `-movflags +faststart` — move moov atom for web playback
- `-pix_fmt yuv420p` — pixel format for broad compatibility

### Seeking & Duration
- `-ss HH:MM:SS` — seek to timestamp (before -i = fast, after -i = accurate)
- `-to HH:MM:SS` — stop at timestamp
- `-t N` — duration in seconds
- `-frames:v N` — stop after N video frames

### Stream Selection
- `-map 0:v:0` — first video stream of first input
- `-map 0:a:0` — first audio stream of first input
- `-vn` — no video
- `-an` — no audio
