# Change Speed (Fast / Slow Motion / Timelapse)

## When to Use

Use speed changes to create dramatic effect, compress long footage into highlights, or produce slow-motion replays. The primary use cases are:
- **2x speed** — compress talking head or tutorial footage.
- **0.5x slow-mo** — emphasize action moments.
- **4x–10x timelapse** — condense long recordings (no audio needed).
- **Smooth slow-mo** — synthesize intermediate frames via `minterpolate` for cinematic look (CPU-heavy).

## Technique

Video speed uses `setpts` (set presentation timestamps):
- **Faster**: `setpts=0.5*PTS` (2x speed — half the timestamps, so frames are presented faster)
- **Slower**: `setpts=2.0*PTS` (0.5x speed — double the timestamps)

The relationship is **inverse**: to play at Nx speed, multiply PTS by `1/N`.

Audio speed uses `atempo`:
- Range is **0.5 to 2.0** per instance.
- To go beyond 2x, **chain multiple `atempo` filters**: `atempo=2.0,atempo=2.0` = 4x.
- For timelapse / no-audio output, use `-an` to drop the audio stream entirely.

`minterpolate` synthesizes new frames using motion interpolation (like optical flow). It makes slow-mo look smooth rather than stuttery when you don't have high-frame-rate source footage. It is significantly slower than `setpts` alone.

## CLI Commands

**2x speed (video + audio):**
```bash
ffmpeg -i input.mp4 \
  -vf "setpts=0.5*PTS" \
  -af "atempo=2.0" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  output_2x.mp4
```

**0.5x slow-motion (video + audio):**
```bash
ffmpeg -i input.mp4 \
  -vf "setpts=2.0*PTS" \
  -af "atempo=0.5" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  output_slowmo.mp4
```

**4x timelapse (video only, no audio):**
```bash
ffmpeg -i input.mp4 \
  -vf "setpts=0.25*PTS" \
  -an \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  output_timelapse.mp4
```

**Smooth slow-motion at 0.5x using minterpolate (frame synthesis):**
```bash
ffmpeg -i input.mp4 \
  -vf "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,setpts=2.0*PTS" \
  -af "atempo=0.5" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  output_smooth_slowmo.mp4
```
This first interpolates to 60fps (synthesizing new frames), then slows down — result is fluid 30fps slow-motion output.

**8x speed with chained atempo (exceeds 2.0 limit):**
```bash
ffmpeg -i input.mp4 \
  -vf "setpts=0.125*PTS" \
  -af "atempo=2.0,atempo=2.0,atempo=2.0" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  output_8x.mp4
```
`2.0 * 2.0 * 2.0 = 8x` audio speed. Three chained `atempo` filters each operating within the valid 0.5–2.0 range.

## Under the Hood

`setpts` modifies the PTS (Presentation Timestamp) of each video frame. By multiplying PTS by 0.5, each frame is told to display at half its original time — so the decoder advances through frames twice as fast. The number of frames in the output is the same as the input; what changes is how fast they're played back.

`atempo` is a time-domain audio stretching filter using WSOLA (Waveform Similarity Overlap-Add). It time-stretches audio without changing pitch (unlike naively resampling). Each instance is limited to 0.5–2.0 because WSOLA quality degrades outside that range; chaining is the recommended workaround.

`minterpolate` (Motion Interpolating) uses optical flow estimation to synthesize frames that didn't exist in the source. `mi_mode=mci` (Motion Compensated Interpolation) produces the highest quality. It is very CPU-intensive — expect 5–20x slower than real-time on typical hardware.

## Sources

- OTTVerse: https://ottverse.com/how-to-speed-up-slow-down-video-playback-using-ffmpeg/
- Shotstack: https://shotstack.io/learn/ffmpeg-speed-up-video-slow-down-videos/
- Creatomate: https://creatomate.com/blog/how-to-speed-up-or-slow-down-video-playback-using-ffmpeg

## Learned from Usage

- `setpts=PTS/2` and `setpts=0.5*PTS` are equivalent — both halve the timestamps.
- For extreme slowdowns (0.25x or slower), `minterpolate` is almost always worth the CPU cost; without it, source frames repeat visibly.
- When the output framerate feels wrong after a speed change, add `-r 30` to force a consistent output frame rate.
- `atempo` for values below 0.5x: chain as `atempo=0.5,atempo=0.5` = 0.25x.
- `-an` (audio none) is the fastest path for timelapse — skips all audio decode/encode.
