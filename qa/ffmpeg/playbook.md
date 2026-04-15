# ffmpeg Skill QA Playbook

## Overview

The ffmpeg skill wraps the `ffmpeg` and `ffprobe` binaries via a Typer CLI at
`skill-repo/ffmpeg/scripts/ffmpeg_cli.py`. It exposes 34 commands across 7
groups. QA is structured in three tiers:

- **Tier 1 (command_graph)** — No binary required. Mock `subprocess.run`, assert
  on the exact args list. Always runs in CI.
- **Tier 2 (integration)** — Requires real `ffmpeg`/`ffprobe` in PATH. Generates
  synthetic input with `lavfi`/`sine` sources and asserts on probe output. Skips
  in CI when binary is absent.
- **Tier 3 (manual)** — Opens output files for human evaluation of visual/aural
  quality. Never runs in CI.

---

## Group: convert

### convert format

Converts between container/codec formats. Two modes:
- `--copy`: stream copy, no re-encoding — fast, lossless, may fail for mismatched
  containers.
- Re-encode (default): libx264 + AAC, adds `-movflags +faststart`.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Copy mode | any .mp4 | same streams, `-c copy`, `-movflags +faststart` | Tier 1: assert `-c copy` in args; Tier 2: codec unchanged |
| Re-encode default (CRF 23) | .mov | .mp4 with libx264 video, AAC audio | Tier 1: assert `-c:v libx264 -crf 23`; Tier 2: probe codec=h264 |
| Re-encode custom CRF | .mp4 | lower-quality .mp4 | Tier 1: assert CRF value propagated |
| Custom codec | .mp4 | libx265 output | Tier 1: assert `-c:v libx265` |

**Edge cases / gotchas**
- Copy mode with mismatched container (e.g., MKV audio to MP4) will silently
  fail or produce unplayable output — re-encode instead.
- `-movflags +faststart` is appended in both modes; required for web playback.

---

### convert compress

CRF-based or two-pass target-size compression.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| CRF mode (default) | .mp4 | smaller .mp4 | Tier 1: assert `-crf 23`, `-c:v libx264` |
| Two-pass target size | .mp4 + `--target-size 10` | ~10 MB output | Tier 1: assert two `subprocess.run` calls; first has `-pass 1 -an -f null`; second has `-pass 2`; Tier 2: file size within 15% of target |
| Duration probe failure | malformed file | exit code 1, error message | Tier 2: assert non-zero exit |

**Edge cases / gotchas**
- Two-pass uses `ffprobe` internally to get duration; if duration returns 0, the
  command exits with code 1.
- Target size too small for duration also exits with code 1.
- Pass 1 writes `ffmpeg2pass` log files in the CWD; clean them up between runs.

---

### convert audio

Extracts or converts audio, auto-detecting codec from output extension.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| .mp3 output | .mp4 | MP3 with `-q:a 2` (VBR) | Tier 1: assert `-vn -c:a libmp3lame -q:a 2` |
| .wav output | .mp4 | PCM WAV | Tier 1: assert `-c:a pcm_s16le` |
| .flac output | .mp4 | FLAC | Tier 1: assert `-c:a flac` |
| CBR override | .mp4 + `--bitrate 192k` | constant bitrate MP3 | Tier 1: assert `-b:a 192k`, no `-q:a` |
| Unknown extension | .mp4 to .xyz | falls back to AAC | Tier 1: assert `-c:a aac` |

---

### convert platform

Encodes to platform-specific optimal settings.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| youtube | .mov | libx264 CRF 18, AAC 384k, 48kHz, `-bf 2 -g 30` | Tier 1: assert CRF, bitrate, `-bf 2` |
| twitter | .mp4 | CRF 23, max 1280x720, padded to even dims | Tier 1: assert scale/pad vf, `-b:a 128k` |
| tiktok | .mp4 | 1080x1920 letterbox, AAC 192k | Tier 1: assert `scale=1080:1920` in vf |
| unknown platform | .mp4 + `--platform vine` | exit code 1 | Tier 1: assert exit_code == 1 |

**Edge cases / gotchas**
- Twitter filter uses `min()` expressions — the single quotes inside the `-vf`
  value must not be shell-escaped when passed as a Python list.
- TikTok output is 9:16 portrait; landscape inputs will be letterboxed with black
  bars on top/bottom.

---

### convert to-gif

Two-pass GIF encoding: palette generation then dithered encode.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Basic conversion | .mp4 | animated .gif, palette-optimized | Tier 1: assert two `subprocess.run` calls; first has `palettegen`; second has `paletteuse` and `-lavfi` |
| With time range | .mp4 + `--start 00:00:01 --duration 2` | 2-second GIF | Tier 1: assert `-ss` and `-t` appear before `-i` in both passes |
| Custom fps/width | .mp4 + `--fps 10 --width 320` | narrower, slower GIF | Tier 1: assert `fps=10,scale=320:-1` in filter string |

**Edge cases / gotchas**
- The palette PNG is written to a `tempfile` and deleted in a `finally` block;
  if pass 1 fails, pass 2 should not run (the CLI currently does not guard this).
- Palette with `stats_mode=diff` produces better results for motion content than
  the default `full` mode.
- Very short clips (< 0.5s) may produce a single-frame GIF — valid but
  unexpected.

---

### convert hwaccel

Hardware-accelerated encoding via nvenc, vaapi, or videotoolbox.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| nvenc H.264 | .mp4 | encoded with `h264_nvenc`, `-cq 23` | Tier 1: assert codec and quality flag |
| vaapi HEVC | .mp4 + `--hevc` | `-vaapi_device /dev/dri/renderD128`, `hevc_vaapi` | Tier 1: assert vaapi device prepended |
| unknown encoder | .mp4 + `--encoder cuda` | exit code 1 | Tier 1: assert exit_code == 1 |

**Edge cases / gotchas**
- vaapi path is Linux-only; test will pass on any platform at Tier 1 since no
  binary is invoked.
- videotoolbox quality range (0–100) differs from CRF semantics — default 65 is
  high quality.

---

## Group: extract

### extract clip

Trims a clip. `-ss` is placed BEFORE `-i` (input-seeking) for accuracy and speed.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Copy mode | .mp4 + `--start 5 --duration 3 --copy` | 3s clip, stream copy | Tier 1: assert `-ss` before `-i`, `-c copy`, `-avoid_negative_ts make_zero` |
| Re-encode mode | .mp4 + `--start 5 --end 8` | 3s re-encoded clip | Tier 1: assert `-c:v libx264 -crf 18`, no `-avoid_negative_ts` |
| End timestamp | .mp4 + `--start 0 --end 00:00:05` | 5s clip | Tier 1: assert `-to 00:00:05` in args |

**Edge cases / gotchas**
- `-ss` before `-i` is fast-seek (keyframe-accurate) but may start slightly
  before the requested timestamp. Re-encode mode corrects this.
- `--copy` with `--end` may cut on a non-keyframe; use `--copy` only when
  precise frame-accuracy is not required.

---

### extract audio

Extracts an audio track with `-vn`.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Default (mp3) | .mp4 to .mp3 | MP3, `-map 0:a:0` | Tier 1: assert `-vn -map 0:a:0 -c:a libmp3lame` |
| Track selection | .mkv + `--track 1` | second audio track | Tier 1: assert `-map 0:a:1` |
| WAV extraction | .mp4 to .wav | PCM 16-bit WAV | Tier 1: assert `-c:a pcm_s16le` |
| CBR bitrate | .mp4 to .mp3 + `--bitrate 320k` | 320kbps MP3 | Tier 1: assert `-b:a 320k`, no `-q:a` |

---

### extract frames

Extracts still frames from video.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Single frame at timestamp | .mp4 + `--at 00:00:01` | one JPEG | Tier 1: assert `-ss` before `-i`, `-frames:v 1` |
| Every N seconds | .mp4 + `--every 1.0` | series of JPEGs | Tier 1: assert `fps=1/1.0` in `-vf` |
| I-frames only | .mp4 + `--iframes` | keyframe JPEGs only | Tier 1: assert `select='eq(pict_type,I)'`, `-vsync vfr` |
| Width scaling | .mp4 + `--width 160` | 160-wide frames | Tier 1: assert `scale=160:-2` in `-vf` |

---

### extract sprite

Generates a thumbnail grid (sprite sheet).

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Default 10x10 | .mp4 | 160x160 tile grid | Tier 1: assert `tile=10x10` in `-vf`; Tier 2: image has correct pixel dimensions |
| Custom cols/rows | .mp4 + `--cols 5 --rows 2` | 5x2 grid | Tier 1: assert `tile=5x2` |

**Edge cases / gotchas**
- Requires `ffprobe` to determine duration before running `ffmpeg`.
- If duration is 0 (non-video or corrupt file), exits with code 1.

---

## Group: transform

### transform resize

Resizes video using `scale` filter with `-2` for even-dimension rounding.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Width only | .mp4 + `--width 1280` | 1280 wide, height auto | Tier 1: assert `scale=1280:-2` |
| Height only | .mp4 + `--height 720` | 720 tall, width auto | Tier 1: assert `scale=-2:720` |
| Both dimensions + letterbox | .mp4 + `--width 1920 --height 1080 --letterbox` | padded to exact size | Tier 1: assert `force_original_aspect_ratio=decrease` and `pad=` in vf |
| No dimensions given | .mp4 | exit code 1 | Tier 1: assert exit_code == 1 |

**Edge cases / gotchas**
- `-2` (not `-1`) ensures divisibility by 2, required by libx264. Using `-1`
  may produce "width not divisible by 2" errors.
- `--letterbox` without both `--width` and `--height` falls through to simple
  scale; the padded path only activates when both are provided.

---

### transform crop

Crops or pads to a target aspect ratio.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| 9:16 crop (default) | 16:9 .mp4 | portrait crop, no black bars | Tier 1: assert `crop=ih*9/16:ih` |
| 16:9 crop | portrait .mp4 + `--aspect 16:9` | landscape crop | Tier 1: assert `crop=ih*16/9:ih` |
| Pad mode | .mp4 + `--pad` | padded with black bars instead of cropped | Tier 1: assert `pad=` in vf |

**Edge cases / gotchas**
- The crop formula keeps full height and adjusts width; for some inputs the
  cropped width could be 0 if aspect is very wide.
- Padding uses `ow-iw` offset expressions; verify even dimensions when piping
  to libx264.

---

### transform speed

Changes playback speed with `setpts` (video) and `atempo` chain (audio).

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| 2x speed | .mp4 + `--factor 2.0` | half duration | Tier 1: assert `setpts=0.5*PTS`, `atempo=2.0` |
| 0.5x slow-mo | .mp4 + `--factor 0.5` | double duration | Tier 1: assert `setpts=2.0*PTS`, `atempo=0.5` |
| 4x speed (chain) | .mp4 + `--factor 4.0` | `atempo=2.0,atempo=2.0` chain | Tier 1: assert two `atempo=2.0` entries |
| No audio | .mp4 + `--factor 2.0 --no-audio` | video only | Tier 1: assert `-an` in args |

**Edge cases / gotchas**
- `atempo` only accepts values 0.5–2.0; the CLI chains multiple filters to
  handle factors outside this range.
- `--interpolate` only activates for slow-mo (factor < 1.0); for speed-up it
  is silently ignored.

---

### transform watermark

Overlays a PNG watermark with optional scale and opacity.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Bottom-right (default) | .mp4 + logo.png | logo at `W-w-10:H-h-10` | Tier 1: assert `overlay=W-w-10:H-h-10` |
| Top-left | .mp4 + `--position tl` | logo at `10:10` | Tier 1: assert `overlay=10:10` |
| With opacity | .mp4 + `--opacity 0.5` | `colorchannelmixer=aa=0.5` in filter | Tier 1: assert `colorchannelmixer` in `-filter_complex` |
| With scale | .mp4 + `--scale 100` | `scale=100:-1` prepended | Tier 1: assert `scale=100:-1` |

---

### transform subtitles

Burns SRT/ASS subtitles into the video stream.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Basic burn | .mp4 + .srt | burned subtitle | Tier 1: assert `subtitles=` in `-vf`; Tier 2: visually check first frame at subtitle timestamp |
| With font size | .mp4 + .srt + `--font-size 24` | `force_style='FontSize=24'` | Tier 1: assert `FontSize=24` in vf |
| Windows path (backslashes) | C:\path\to\file.srt | backslashes converted to `/`, colons escaped | Tier 1: assert no raw backslashes in filter string |

**Edge cases / gotchas**
- The subtitle filter requires libass; some ffmpeg builds omit it.
- Colons in Windows drive letters (e.g., `C:`) must be escaped as `\:` in the
  filter string — the CLI handles this.

---

### transform rotate

Rotates or flips video using `transpose` filter.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| 90 degrees CW | .mp4 + `--angle 90` | `transpose=1` | Tier 1: assert `transpose=1` |
| 180 degrees | .mp4 + `--angle 180` | `transpose=1,transpose=1` | Tier 1: assert two transpose filters |
| 270 degrees CW | .mp4 + `--angle 270` | `transpose=2` | Tier 1: assert `transpose=2` |
| Horizontal flip | .mp4 + `--flip h` | `hflip` | Tier 1: assert `hflip` in vf |
| Vertical flip | .mp4 + `--flip v` | `vflip` | Tier 1: assert `vflip` in vf |
| No args | .mp4 (no flags) | exit code 1 | Tier 1: assert exit_code == 1 |
| Invalid angle | .mp4 + `--angle 45` | exit code 1 | Tier 1: assert exit_code == 1 |

---

### transform fade

Adds fade in/out with synchronized audio and video filters.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Fade in only | .mp4 + `--fade-in 1.0` | `fade=t=in:st=0:d=1.0`, `afade=t=in:st=0:d=1.0` | Tier 1: assert both vf and af entries |
| Fade out only | .mp4 + `--fade-out 1.0` | fade starts at `duration - 1.0` | Tier 1: assert `st=` value near end |
| No args | .mp4 | exit code 1 | Tier 1: assert exit_code == 1 |

**Edge cases / gotchas**
- Requires `ffprobe` call to get duration for fade-out start time.
- If file has no audio, `-af` is still passed — ffmpeg will warn but succeed.

---

## Group: audio

### audio normalize

EBU R128 two-pass loudness normalization.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Default (-16 LUFS) | loud .wav | pass 1 measures loudness, pass 2 normalizes | Tier 1: assert two `subprocess.run` calls; first has `loudnorm=I=-16` and `-f null`; second has `measured_I=` and `-ar 48000` |
| Custom target | .wav + `--target -23` | normalized to -23 LUFS | Tier 1: assert `loudnorm=I=-23` |
| ffmpeg JSON parse failure | mock bad stderr | exit code 1 | Tier 1: mock `subprocess.run` to return malformed stderr |

**Edge cases / gotchas**
- The JSON measurements are parsed from `stderr` (not stdout); the CLI extracts
  the last JSON object by scanning backwards for `{`/`}` brace pairs.
- If ffmpeg's stderr format changes, the JSON parse will fail silently and exit 1.
- Pass 1 uses `check=False` to tolerate non-zero exits (ffmpeg exits 0 here but
  some builds differ).

---

### audio silence

Removes silence using the `silenceremove` filter.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Default | .wav with silence | shorter output | Tier 1: assert `silenceremove=stop_periods=-1` in `-af` |
| Custom threshold | + `--threshold -40dB` | threshold in filter | Tier 1: assert `stop_threshold=-40dB` |
| Keep padding | + `--keep-padding 0.5` | `stop_silence=0.5` | Tier 1: assert value in filter |

---

### audio denoise

Reduces background noise via FFT or RNN.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| FFT (default) | noisy .wav | `afftdn=nr=12:nf=-45:tn=1` | Tier 1: assert filter string |
| FFT custom strength | + `--strength 20` | `nr=20` | Tier 1: assert nr value |
| RNN | noisy .wav + `--method rnn --model path/to.rnnn` | `arnndn=m=...` | Tier 1: assert `arnndn` filter |
| RNN without model | + `--method rnn` | exit code 1 | Tier 1: assert exit_code == 1 |

---

### audio duck

Ducks background music under voice using volume or sidechain compression.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Static ducking (default 0.15) | voice.wav + music.mp3 | `volume=0.15`, `amix` | Tier 1: assert `volume=0.15` in `-filter_complex` |
| Dynamic sidechain | + `--dynamic` | `sidechaincompress` in filter | Tier 1: assert `sidechaincompress` |
| Custom level | + `--music-level 0.3` | `volume=0.3` | Tier 1: assert value |

---

## Group: combine

### combine concat

Concatenates files using demuxer (default) or concat filter (`--filter`).

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Demuxer mode (2 files) | a.mp4 + b.mp4 | combined .mp4, stream copy | Tier 1: assert `-f concat -safe 0 -i <filelist> -c copy` |
| Filter mode | a.mp4 + b.mp4 + `--filter` | combined with re-encode | Tier 1: assert `-filter_complex` with `concat=n=2:v=1:a=1` |
| Three files | a.mp4 + b.mp4 + c.mp4 | concatenated | Tier 1: assert `concat=n=3` (filter mode) |

**Edge cases / gotchas**
- Demuxer mode writes a temp `.txt` filelist with absolute paths (backslashes
  converted to forward slashes). The file is deleted in a `finally` block.
- Demuxer mode requires identical codec/resolution; use `--filter` for mismatched
  inputs.
- The temp filelist path is not deterministic; Tier 1 tests should check args
  positionally (e.g., args[1] == "concat") rather than the exact filelist path.

---

### combine mux

Muxes separate video and audio files.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Basic mux | video.mp4 + audio.wav | combined output, stream copy | Tier 1: assert `-map 0:v:0 -map 1:a:0 -c copy` |
| With delay | + `--delay 0.5` | `-itsoffset 0.5` before second `-i` | Tier 1: assert `-itsoffset 0.5` precedes audio `-i` |

---

### combine from-images

Creates video from an image sequence.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Default 24fps | frame_%04d.png | .mp4 at 24fps | Tier 1: assert `-framerate 24 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p` |
| Custom framerate | + `--framerate 30` | 30fps output | Tier 1: assert `-framerate 30` |

---

### combine composite

Composites multiple videos with pip, side-by-side, or grid layout.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| pip | 2 files | main + small overlay at bottom-right | Tier 1: assert `overlay=W-w-10:H-h-10` in `-filter_complex` |
| side-by-side | 2 files | hstack output | Tier 1: assert `hstack=inputs=2` |
| grid (4 files) | 4 files | 2x2 grid | Tier 1: assert `vstack` and `hstack` both present |
| unknown layout | + `--layout diagonal` | exit code 1 | Tier 1: assert exit_code == 1 |

---

## Group: stream

### stream hls

Generates multi-quality HLS with a master playlist.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Default 3 qualities | .mp4 + output_dir | `master.m3u8` + per-quality streams | Tier 1: assert `-f hls`, `-hls_playlist_type vod`, `split=3` in filter |
| Single quality | + `--qualities 720p` | one rendition | Tier 1: assert `split=1` |

**Manual verification**: Open `master.m3u8` in VLC; confirm quality switching
works (right-click > Subtitles > Audio track shows multiple renditions).

---

### stream dash

Generates DASH manifest with multiple adaptation sets.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Default 3 qualities | .mp4 + output_dir | `manifest.mpd` | Tier 1: assert `-f dash`, `adaptation_sets` arg |

---

### stream ladder

Encodes a separate MP4 per quality level.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Default 3 qualities | .mp4 + output_dir | `1080p.mp4`, `720p.mp4`, `480p.mp4` | Tier 1: assert 3 `subprocess.run` calls; Tier 2: probe each file |

---

### stream restream

Re-streams to multiple RTMP endpoints via tee muxer.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Two destinations | stream.mp4 + 2 URLs | `-f tee` with both URLs piped | Tier 1: assert `-f tee` and both URLs in tee_parts |

**Edge cases / gotchas**: Live testing requires an actual RTMP server; use
nginx-rtmp or a local restream.io endpoint.

---

### stream fake-live

Streams a file to RTMP with `-re` (real-time pacing).

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Basic | file.mp4 + rtmp URL | `-re -i file.mp4 ... -f flv` | Tier 1: assert `-re` first arg, `-f flv` |
| Loop | + `--loop` | `-stream_loop -1` before `-i` | Tier 1: assert `-stream_loop -1` |
| Playlist | + `--playlist filelist.txt` | `-f concat -safe 0 -i filelist.txt` | Tier 1: assert concat mode |

---

## Group: util

### util probe

Runs `ffprobe` and displays format/stream info.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Default (rich table) | .mp4 | formatted tables to stdout | Tier 1: assert ffprobe args include `-print_format json -show_format -show_streams`; Tier 2: assert output contains "Format" text |
| JSON mode | .mp4 + `--json` | raw JSON to stdout | Tier 2: assert `json.loads(result.output)` succeeds |

---

### util batch

Batch-transcodes all video files in a directory.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Mixed directory | dir with .mp4, .avi, .txt | only .mp4 and .avi transcoded | Tier 1: assert one ffmpeg call per video; Tier 2: assert output files exist |
| Skip existing | output file already present | ffmpeg not called for that file | Tier 2: assert second run produces no new ffmpeg calls |
| Custom CRF | + `--crf 18` | CRF 18 in args | Tier 1: assert `-crf 18` |

---

### util record

Screen capture (platform-detected input device).

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Windows | platform=win32 | `-f gdigrab -framerate N -i desktop` | Tier 1: mock `sys.platform == "win32"`, assert `gdigrab` |
| macOS | platform=darwin | `-f avfoundation -framerate N -i 1:none` | Tier 1: mock platform |
| Linux | platform=linux | `-f x11grab` | Tier 1: mock platform |
| With audio (Windows) | + `--audio` | `-f dshow -i audio=virtual-audio-capturer` | Tier 1: assert dshow args |

**Edge cases / gotchas**: Actual screen capture requires elevated permissions
on macOS and a valid `DISPLAY` on Linux. Tier 1 only.

---

### util surveillance

Records an RTSP stream to time-stamped segments.

| Scenario | Input | Expected output | Verify |
|---|---|---|---|
| Basic | rtsp://... + output_dir | `-rtsp_transport tcp`, `-f segment`, `strftime` pattern | Tier 1: assert all required flags |
| Custom segment time | + `--segment-time 300` | `-segment_time 300` | Tier 1: assert value |

---

## Manual Verification Guide

These checks cannot be automated and require a human reviewer:

1. **Visual quality** — Open convert outputs in a video player. Check for:
   - No blocking artifacts at CRF 23 for typical content
   - Correct orientation after rotate operations
   - Watermark positioned correctly and at expected opacity
   - Subtitles readable, correctly timed, correctly positioned

2. **Audio quality** — Listen to audio normalize output:
   - Volume is consistent across a batch of clips
   - No audible clipping or pumping artifacts
   - Silence removal does not cut words at sentence boundaries

3. **GIF quality** — Open GIF output in a browser:
   - Smooth motion, no excessive dithering
   - Palette covers the main colors of the source
   - Loop plays continuously

4. **Platform encode** — Upload to each platform in a test account:
   - YouTube: check that the player does not re-transcode (look for 4K/8K badge)
   - TikTok: confirm portrait fill with no letter/pillar bar cropping issues

5. **HLS playback** — Serve `master.m3u8` locally (e.g., `python -m http.server`):
   - Play in Safari or with `ffplay`; confirm quality levels are listed
   - Verify bitrate switching under throttled network (DevTools Network tab)

---

## Known Limitations and Gotchas Summary

| Command | Limitation |
|---|---|
| `convert compress` | Two-pass log files accumulate in CWD |
| `convert to-gif` | No guard if pass 1 fails; pass 2 still attempted |
| `audio normalize` | JSON parse from stderr is fragile; format changes will break it |
| `transform subtitles` | Requires libass; not present in all ffmpeg builds |
| `transform fade` | Passes `-af` even for video-only files |
| `combine concat` (demuxer) | Fails silently with mismatched codecs; use `--filter` |
| `util probe` | Imports `rich` at call time; will fail if `rich` not installed |
| `stream ladder` | Builds multi-output arg list but then discards it; runs separate commands per quality instead |
