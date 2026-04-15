# ffmpeg Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first cli-me skill — a complete ffmpeg wrapper with 35 technique wiki pages and an intent-based Typer CLI.

**Architecture:** The skill follows the cli-me pattern: SKILL.md for Claude trigger/instructions, scripts/ with a self-contained Typer CLI (own pyproject.toml), and references/ as a Karpathy-pattern LLM wiki with 35 technique pages organized in 7 categories. The Typer CLI shells out to the real ffmpeg/ffprobe binary — it never processes media in Python.

**Tech Stack:** Python 3.12+, Typer, ffmpeg/ffprobe (subprocess), Markdown wiki

**Spec:** `docs/superpowers/specs/2026-04-15-ffmpeg-skill-design.md`

**Parallelization note:** Tasks 2-8 (wiki categories) are fully independent and should be dispatched in parallel. Tasks 10-16 (CLI command groups) are also independent and can run in parallel after Task 9 (CLI scaffold) completes.

---

## File Map

### Skill Root
- Create: `skill-repo/ffmpeg/SKILL.md`

### Scripts
- Create: `skill-repo/ffmpeg/scripts/pyproject.toml`
- Create: `skill-repo/ffmpeg/scripts/ffmpeg_cli.py`

### Wiki — Operational
- Create: `skill-repo/ffmpeg/references/index.md`
- Create: `skill-repo/ffmpeg/references/log.md`
- Create: `skill-repo/ffmpeg/references/gotchas.md`

### Wiki — Source Analysis
- Create: `skill-repo/ffmpeg/references/source-analysis/analyzed-version.md`
- Create: `skill-repo/ffmpeg/references/source-analysis/api-surface.md`
- Create: `skill-repo/ffmpeg/references/source-analysis/cli-interface.md`
- Create: `skill-repo/ffmpeg/references/source-analysis/changelog.md`

### Wiki — Techniques (35 pages)
- Create: `skill-repo/ffmpeg/references/techniques/convert-video-format.md`
- Create: `skill-repo/ffmpeg/references/techniques/compress-video.md`
- Create: `skill-repo/ffmpeg/references/techniques/convert-audio-format.md`
- Create: `skill-repo/ffmpeg/references/techniques/platform-encoding.md`
- Create: `skill-repo/ffmpeg/references/techniques/hardware-encoding.md`
- Create: `skill-repo/ffmpeg/references/techniques/trim-clip.md`
- Create: `skill-repo/ffmpeg/references/techniques/extract-audio.md`
- Create: `skill-repo/ffmpeg/references/techniques/extract-frames.md`
- Create: `skill-repo/ffmpeg/references/techniques/sprite-sheet.md`
- Create: `skill-repo/ffmpeg/references/techniques/surveillance-clip.md`
- Create: `skill-repo/ffmpeg/references/techniques/resize-scale.md`
- Create: `skill-repo/ffmpeg/references/techniques/crop-vertical.md`
- Create: `skill-repo/ffmpeg/references/techniques/change-speed.md`
- Create: `skill-repo/ffmpeg/references/techniques/watermark-overlay.md`
- Create: `skill-repo/ffmpeg/references/techniques/burn-subtitles.md`
- Create: `skill-repo/ffmpeg/references/techniques/rotate-flip.md`
- Create: `skill-repo/ffmpeg/references/techniques/fade-transitions.md`
- Create: `skill-repo/ffmpeg/references/techniques/normalize-loudness.md`
- Create: `skill-repo/ffmpeg/references/techniques/remove-silence.md`
- Create: `skill-repo/ffmpeg/references/techniques/denoise-audio.md`
- Create: `skill-repo/ffmpeg/references/techniques/music-ducking.md`
- Create: `skill-repo/ffmpeg/references/techniques/concatenate-clips.md`
- Create: `skill-repo/ffmpeg/references/techniques/mux-audio-video.md`
- Create: `skill-repo/ffmpeg/references/techniques/image-sequence-to-video.md`
- Create: `skill-repo/ffmpeg/references/techniques/complex-filtergraph.md`
- Create: `skill-repo/ffmpeg/references/techniques/hls-segments.md`
- Create: `skill-repo/ffmpeg/references/techniques/dash-segments.md`
- Create: `skill-repo/ffmpeg/references/techniques/multi-bitrate.md`
- Create: `skill-repo/ffmpeg/references/techniques/rtmp-restream.md`
- Create: `skill-repo/ffmpeg/references/techniques/fake-live-stream.md`
- Create: `skill-repo/ffmpeg/references/techniques/batch-transcode.md`
- Create: `skill-repo/ffmpeg/references/techniques/ffprobe-validate.md`
- Create: `skill-repo/ffmpeg/references/techniques/rtsp-recording.md`
- Create: `skill-repo/ffmpeg/references/techniques/video-to-gif.md`
- Create: `skill-repo/ffmpeg/references/techniques/screen-capture.md`

### Registry
- Modify: `skill-repo/registry.json`

### Tests
- Create: `tests/test_ffmpeg_skill.py`

---

## Task 1: Scaffold — Directory Structure, SKILL.md, Registry

**Files:**
- Create: `skill-repo/ffmpeg/SKILL.md`
- Create: `skill-repo/ffmpeg/scripts/pyproject.toml`
- Create: `skill-repo/ffmpeg/references/index.md`
- Create: `skill-repo/ffmpeg/references/log.md`
- Create: `skill-repo/ffmpeg/references/gotchas.md`
- Create: `skill-repo/ffmpeg/references/source-analysis/analyzed-version.md`
- Create: `skill-repo/ffmpeg/references/source-analysis/api-surface.md`
- Create: `skill-repo/ffmpeg/references/source-analysis/cli-interface.md`
- Create: `skill-repo/ffmpeg/references/source-analysis/changelog.md`
- Modify: `skill-repo/registry.json`

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p skill-repo/ffmpeg/scripts
mkdir -p skill-repo/ffmpeg/references/source-analysis
mkdir -p skill-repo/ffmpeg/references/techniques
```

- [ ] **Step 2: Write SKILL.md**

Create `skill-repo/ffmpeg/SKILL.md`:

```markdown
---
name: ffmpeg
description: Media processing CLI for ffmpeg. Use when asked to convert video, compress
  video, extract audio, trim or clip video, resize video, add subtitles, remove
  background noise, normalize audio, create gif, stream video, HLS, DASH, RTMP,
  concatenate or merge videos, add watermark, create timelapse, slow motion, screen
  capture, ffprobe, podcast audio processing, or any media file manipulation.
---

# ffmpeg — cli-me skill

Intent-based CLI for ffmpeg and ffprobe. This skill wraps the real ffmpeg binary —
it does not process media in Python.

## Prerequisites

- ffmpeg and ffprobe must be installed and in PATH
  - Windows: `winget install ffmpeg` or download from https://ffmpeg.org/download.html
  - macOS: `brew install ffmpeg`
  - Linux: `apt install ffmpeg` or `dnf install ffmpeg`
- Python 3.12+

## CLI Commands

Run commands via:
```bash
uv run scripts/ffmpeg_cli.py <group> <command> [options]
```

### Command Groups

| Group | Purpose |
|-------|---------|
| `convert` | Format conversion, compression, platform encoding, GIF, hardware accel |
| `extract` | Trim clips, extract audio, frames, sprite sheets |
| `transform` | Resize, crop, speed, watermark, subtitles, rotate, fade |
| `audio` | Normalize loudness, denoise, remove silence, music ducking |
| `combine` | Concatenate, mux audio+video, image sequences, compositing |
| `stream` | HLS, DASH, multi-bitrate, RTMP restream, fake live |
| `util` | Batch transcode, probe/validate, screen capture, surveillance |

### Quick Examples

```bash
# Convert MOV to MP4
uv run scripts/ffmpeg_cli.py convert format input.mov output.mp4

# Compress for web
uv run scripts/ffmpeg_cli.py convert compress input.mp4 output.mp4 --crf 23

# Extract audio as MP3
uv run scripts/ffmpeg_cli.py extract audio input.mp4 output.mp3

# Trim a clip
uv run scripts/ffmpeg_cli.py extract clip input.mp4 output.mp4 --start 00:01:30 --end 00:02:00

# Resize to 720p
uv run scripts/ffmpeg_cli.py transform resize input.mp4 output.mp4 --height 720

# Normalize podcast audio
uv run scripts/ffmpeg_cli.py audio normalize input.wav output.wav --target -16

# Create GIF
uv run scripts/ffmpeg_cli.py convert to-gif input.mp4 output.gif --fps 15 --width 480

# Probe file info
uv run scripts/ffmpeg_cli.py util probe input.mp4
```

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how a command works under the hood, check the
relevant technique page — it explains the ffmpeg flags, common mistakes,
and parameter recommendations.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Append a timestamped entry to `references/log.md` with what you did and
   what you learned
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
```

- [ ] **Step 3: Write scripts/pyproject.toml**

Create `skill-repo/ffmpeg/scripts/pyproject.toml`:

```toml
[project]
name = "ffmpeg-cli"
version = "0.1.0"
description = "Agent-native CLI for ffmpeg"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15.0",
]

[project.scripts]
ffmpeg-cli = "ffmpeg_cli:app"
```

- [ ] **Step 4: Write source analysis pages**

Create `skill-repo/ffmpeg/references/source-analysis/analyzed-version.md`:

```markdown
# Analyzed Version

**Current:** ffmpeg (research conducted 2026-04-15, not tied to a specific source checkout)

ffmpeg is distributed as a compiled binary. Source analysis was conducted against
the public documentation, community guides, and the ffmpeg CLI interface rather
than the C source code. This is appropriate because ffmpeg's value is its CLI
interface, not its internals.

## Analysis History

| Date | Notes |
|------|-------|
| 2026-04-15 | Initial research: 35 workflows documented from 10 parallel research agents |
```

Create `skill-repo/ffmpeg/references/source-analysis/api-surface.md`:

```markdown
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
```

Create `skill-repo/ffmpeg/references/source-analysis/cli-interface.md`:

```markdown
# ffmpeg CLI Interface

## Invocation Patterns

### Single input, single output (most common)
```bash
ffmpeg -i input.mp4 [filters] [codec options] output.mp4
```

### Fast seeking (put -ss before -i)
```bash
ffmpeg -ss 00:01:00 -i input.mp4 -to 00:02:00 [options] output.mp4
```

### Multi-input (requires -filter_complex and -map)
```bash
ffmpeg -i video.mp4 -i audio.aac -filter_complex "..." -map "[v]" -map "[a]" output.mp4
```

### Pipe to null (analysis only, no output file)
```bash
ffmpeg -i input.mp4 -af "loudnorm=print_format=json" -f null -
```

### Batch via shell loop
```bash
for f in *.mov; do ffmpeg -nostdin -i "$f" [options] "${f%.mov}.mp4"; done
```

## ffprobe Patterns

### JSON output (best for scripting)
```bash
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4
```

### Specific field extraction
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 input.mp4
```

## Error Handling

ffmpeg exit codes:
- 0 = success
- 1 = generic error (check stderr)
- 69 = unavailable (codec not compiled in)

Always capture stderr — ffmpeg writes progress and errors there, not stdout.

## Platform Notes

- Windows: use forward slashes in paths or escape backslashes. Use `NUL` instead of `/dev/null`.
- macOS: ffmpeg from Homebrew includes most codecs. The Apple Silicon build includes VideoToolbox.
- Linux: distribution builds may lack non-free codecs (libfdk_aac, libx264). Use static builds from https://johnvansickle.com/ffmpeg/ for full codec support.
```

Create `skill-repo/ffmpeg/references/source-analysis/changelog.md`:

```markdown
# Changelog

Version deltas for the ffmpeg CLI interface. Updated when significant
ffmpeg releases change behavior relevant to this skill.

No entries yet — will be populated when ffmpeg version changes affect
the commands documented in this skill.
```

- [ ] **Step 5: Write wiki operational files**

Create `skill-repo/ffmpeg/references/index.md`:

```markdown
# ffmpeg Knowledge Base

## Source Analysis
- [Analyzed Version](source-analysis/analyzed-version.md) — analysis metadata
- [API Surface](source-analysis/api-surface.md) — ffmpeg flags, filters, codecs
- [CLI Interface](source-analysis/cli-interface.md) — invocation patterns, ffprobe
- [Changelog](source-analysis/changelog.md) — version deltas

## Techniques — Convert & Compress
- [Convert Video Format](techniques/convert-video-format.md) — MOV/AVI/MKV to MP4
- [Compress Video](techniques/compress-video.md) — CRF tuning, two-pass
- [Convert Audio Format](techniques/convert-audio-format.md) — WAV/FLAC to MP3/AAC
- [Platform Encoding](techniques/platform-encoding.md) — YouTube, Twitter, TikTok specs
- [Hardware Encoding](techniques/hardware-encoding.md) — NVENC, VAAPI, VideoToolbox

## Techniques — Trim & Extract
- [Trim/Clip Video](techniques/trim-clip.md) — cut by timestamp
- [Extract Audio](techniques/extract-audio.md) — rip audio track
- [Extract Frames](techniques/extract-frames.md) — thumbnails, every Nth frame
- [Sprite Sheet](techniques/sprite-sheet.md) — tiled preview image
- [Surveillance Clip](techniques/surveillance-clip.md) — extract from rolling archive

## Techniques — Transform & Filter
- [Resize/Scale](techniques/resize-scale.md) — resolution changes
- [Crop to Vertical](techniques/crop-vertical.md) — landscape to 9:16
- [Change Speed](techniques/change-speed.md) — slow-mo, fast-forward, timelapse
- [Watermark Overlay](techniques/watermark-overlay.md) — logo/branding
- [Burn Subtitles](techniques/burn-subtitles.md) — SRT/ASS hardcoding
- [Rotate/Flip](techniques/rotate-flip.md) — orientation fixes
- [Fade Transitions](techniques/fade-transitions.md) — fade in/out

## Techniques — Audio Processing
- [Normalize Loudness](techniques/normalize-loudness.md) — EBU R128, LUFS
- [Remove Silence](techniques/remove-silence.md) — dead air trimming
- [Denoise Audio](techniques/denoise-audio.md) — background noise removal
- [Music Ducking](techniques/music-ducking.md) — mix music under voiceover

## Techniques — Combine & Assemble
- [Concatenate Clips](techniques/concatenate-clips.md) — join multiple videos
- [Mux Audio + Video](techniques/mux-audio-video.md) — combine separate tracks
- [Image Sequence to Video](techniques/image-sequence-to-video.md) — animation/timelapse
- [Complex Filtergraph](techniques/complex-filtergraph.md) — PiP, side-by-side, grid

## Techniques — Streaming & Distribution
- [HLS Segments](techniques/hls-segments.md) — adaptive .m3u8 + .ts
- [DASH Segments](techniques/dash-segments.md) — .mpd + .m4s
- [Multi-Bitrate](techniques/multi-bitrate.md) — adaptive bitrate ladder
- [RTMP Restream](techniques/rtmp-restream.md) — fan-out to multiple platforms
- [Fake Live Stream](techniques/fake-live-stream.md) — pre-recorded as live

## Techniques — Utilities
- [Batch Transcode](techniques/batch-transcode.md) — directory processing
- [ffprobe Validate](techniques/ffprobe-validate.md) — probe and compliance
- [RTSP Recording](techniques/rtsp-recording.md) — surveillance camera capture
- [Video to GIF](techniques/video-to-gif.md) — palette-optimized conversion
- [Screen Capture](techniques/screen-capture.md) — desktop recording

## Operational
- [Gotchas](gotchas.md) — cross-cutting issues and workarounds
- [Learning Log](log.md) — chronological record of learnings
```

Create `skill-repo/ffmpeg/references/log.md`:

```markdown
# Learning Log

Append-only chronological record. Newest entries at the bottom.

---

**2026-04-15** — Initial research completed. 35 technique pages created from
10 parallel research agents covering developer, content creator, and automation
perspectives. Source URLs preserved on every page.
```

Create `skill-repo/ffmpeg/references/gotchas.md`:

```markdown
# Gotchas

Cross-cutting issues and workarounds discovered through research and usage.

## pix_fmt yuv420p
Always include `-pix_fmt yuv420p` when encoding H.264 for web delivery. Without it,
ffmpeg may output yuv444p or yuv422p which breaks in browsers, QuickTime, and iOS.

## -ss placement
`-ss` before `-i` = fast (seeks to nearest keyframe). `-ss` after `-i` = accurate
(decodes from start). For most work, put it before `-i` and re-encode for frame accuracy.

## Windows paths
Windows backslashes and colons need escaping in filter strings. Use forward slashes
or escape: `subtitles='C\\:/path/to/file.srt'`

## -nostdin for batch
When running ffmpeg in a shell loop, add `-nostdin` before `-i` to prevent ffmpeg
from consuming stdin and killing the loop.

## Stream copy limitations
`-c copy` cannot be used with any filter (`-vf`, `-af`, `-filter_complex`).
It also cannot cut at arbitrary frames — only at keyframes.

## ffmpeg.org wiki blocked
As of April 2026, trac.ffmpeg.org returns Anubis anti-bot errors for automated access.
Use community resources (OTTVerse, Mux articles, Stack Overflow) for reference.
```

- [ ] **Step 6: Add registry entry**

Modify `skill-repo/registry.json` — add the ffmpeg skill:

```json
{
  "skills": [
    {
      "name": "ffmpeg",
      "description": "Media processing CLI for ffmpeg — convert, compress, trim, transform, process audio, combine, stream, and batch process video/audio files",
      "category": "media",
      "tags": ["video", "audio", "ffmpeg", "conversion", "compression", "streaming", "hls", "dash", "gif", "podcast", "encoding"],
      "version": "0.1.0",
      "software_url": "https://ffmpeg.org",
      "source_repo": "https://git.ffmpeg.org/ffmpeg.git",
      "dependencies": []
    }
  ]
}
```

- [ ] **Step 7: Commit**

```bash
git add skill-repo/ffmpeg/ skill-repo/registry.json
git commit -m "feat(ffmpeg): scaffold skill with SKILL.md, wiki structure, and registry entry"
```

---

## Tasks 2-8: Wiki Technique Pages

These 7 tasks are **fully independent** and should be dispatched in parallel. Each task writes the technique pages for one category. The content was researched by parallel agents and is provided in the spec conversation — the implementing agent should write each page following the three-layer structure (When to Use, Technique, CLI Commands, Under the Hood, Sources, Learned from Usage).

Every technique page must follow this template:

```markdown
# [Technique Name]

## When to Use
[Specific scenarios]

## Technique
[Domain knowledge: what it does, parameters, best practices, common mistakes]

## CLI Commands
[Real ffmpeg commands with 2-3 variants for common scenarios]

## Under the Hood
[What ffmpeg is doing internally — codecs, filters, flags explained]

## Sources
[URLs for attribution and deeper reading]

## Learned from Usage
[Empty — will be populated as agents use the skill]
```

### Task 2: Wiki — Convert & Compress (5 pages)

**Files:**
- Create: `skill-repo/ffmpeg/references/techniques/convert-video-format.md`
- Create: `skill-repo/ffmpeg/references/techniques/compress-video.md`
- Create: `skill-repo/ffmpeg/references/techniques/convert-audio-format.md`
- Create: `skill-repo/ffmpeg/references/techniques/platform-encoding.md`
- Create: `skill-repo/ffmpeg/references/techniques/hardware-encoding.md`

- [ ] **Step 1: Write all 5 technique pages**

Write each page using the researched content. Key points per page:

**convert-video-format.md:** Transmux (-c copy) vs re-encode decision. ffprobe to check source codec. `-pix_fmt yuv420p` always. `-movflags +faststart` for web. Common: MOV→MP4, AVI→MP4, MKV→MP4.

**compress-video.md:** CRF scale by codec (x264: 0-51, default 23; x265: 0-51, default 28; VP9: 0-63; AV1: 0-63). Preset tradeoffs. Two-pass for target file size with formula: `(target_MB × 8192 / duration_seconds) - audio_kbps = video_kbps`. CRF ±6 ≈ 2x file size change.

**convert-audio-format.md:** Always transcode from lossless source. MP3: VBR `-q:a 0-9`, CBR `-b:a 320k`. AAC: native encoder `-b:a 256k`, libfdk_aac with `-afterburner 1`. FLAC: `-compression_level 8`. Cardinal rule: never lossy→lossy.

**platform-encoding.md:** YouTube (H.264 High, `-g 30`, `-bf 2`, AAC 384k 48kHz). Twitter (H.264 High level 4.0, yuv420p mandatory, max 1920×1200). TikTok (1080×1920, H.264 High level 4.2, 30fps, 8-15 Mbps). Include complete commands for each.

**hardware-encoding.md:** NVENC (`-hwaccel cuda -hwaccel_output_format cuda`, `-rc vbr -cq 23`, presets p1-p7). VAAPI (`format=nv12,hwupload`, `-qp 19`). VideoToolbox (`-q:v 65`, 0-100 scale). Include full commands for each platform.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/references/techniques/convert-*.md skill-repo/ffmpeg/references/techniques/compress-video.md skill-repo/ffmpeg/references/techniques/platform-encoding.md skill-repo/ffmpeg/references/techniques/hardware-encoding.md
git commit -m "feat(ffmpeg): add convert & compress technique pages"
```

### Task 3: Wiki — Trim & Extract (5 pages)

**Files:**
- Create: `skill-repo/ffmpeg/references/techniques/trim-clip.md`
- Create: `skill-repo/ffmpeg/references/techniques/extract-audio.md`
- Create: `skill-repo/ffmpeg/references/techniques/extract-frames.md`
- Create: `skill-repo/ffmpeg/references/techniques/sprite-sheet.md`
- Create: `skill-repo/ffmpeg/references/techniques/surveillance-clip.md`

- [ ] **Step 1: Write all 5 technique pages**

**trim-clip.md:** The critical `-ss` placement difference (before vs after `-i`). Stream copy vs re-encode. `-t` vs `-to`. `-avoid_negative_ts make_zero`. Best-of-both: `-ss` before `-i` + re-encode for fast + accurate.

**extract-audio.md:** `-vn` flag. `-c:a copy` when format matches. MP3 quality (`-q:a 2` for VBR, `-b:a 192k` for CBR). AAC 128k matches MP3 192k. `-map 0:a:1` for multi-track. WAV: `pcm_s16le` for 16-bit.

**extract-frames.md:** Single frame at timestamp (`-frames:v 1`). `thumbnail` filter for auto-selection. `fps=1/N` for interval-based. `select='not(mod(n,N))'` with `-vsync vfr`. I-frames only: `select='eq(pict_type,I)'`.

**sprite-sheet.md:** `tile=COLSxROWS` filter. Compute interval from duration. `-frames:v 1` for single output. Scene-change grid (`select='gt(scene,0.4)'`). Padding and margin options.

**surveillance-clip.md:** Single file extraction with `-ss`/`-to`. Segmented archive with concat demuxer. Motion detection with `select` + `metadata=print`. Shell loop for rolling archive recording. Buffer padding around events.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/references/techniques/trim-clip.md skill-repo/ffmpeg/references/techniques/extract-*.md skill-repo/ffmpeg/references/techniques/sprite-sheet.md skill-repo/ffmpeg/references/techniques/surveillance-clip.md
git commit -m "feat(ffmpeg): add trim & extract technique pages"
```

### Task 4: Wiki — Transform & Filter (7 pages)

**Files:**
- Create: `skill-repo/ffmpeg/references/techniques/resize-scale.md`
- Create: `skill-repo/ffmpeg/references/techniques/crop-vertical.md`
- Create: `skill-repo/ffmpeg/references/techniques/change-speed.md`
- Create: `skill-repo/ffmpeg/references/techniques/watermark-overlay.md`
- Create: `skill-repo/ffmpeg/references/techniques/burn-subtitles.md`
- Create: `skill-repo/ffmpeg/references/techniques/rotate-flip.md`
- Create: `skill-repo/ffmpeg/references/techniques/fade-transitions.md`

- [ ] **Step 1: Write all 7 technique pages**

**resize-scale.md:** `-2` not `-1` for even dimensions. `lanczos` for quality. Letterbox with `force_original_aspect_ratio=decrease,pad`. `-pix_fmt yuv420p` always.

**crop-vertical.md:** `crop=ih*9/16:ih:(iw-ih*9/16)/2:0` then `scale=1080:1920`. Pad approach for full-frame preservation. `-movflags +faststart`. Target 1080×1920 for all short-form platforms.

**change-speed.md:** `setpts=0.5*PTS` for 2x fast, `atempo=2.0` for audio. Inverse relationship. Chain `atempo` for >2x. `minterpolate` for smooth slow-mo (CPU-heavy). Drop audio with `-an` for timelapse.

**watermark-overlay.md:** `-filter_complex` required for 2 inputs. Position shortcuts with `W`, `H`, `w`, `h`. Opacity via `colorchannelmixer=aa=0.5`. Scale logo with `scale=150:-1`. Timed overlay with `enable='between(t,0,5)'`.

**burn-subtitles.md:** `subtitles=file.srt` for hard subs (requires libass). `force_style=` for font/color/position. ASS color format `&HAABBGGRR` (BGR not RGB). Soft subs: `-c:s mov_text`. Windows path escaping. Must re-encode video.

**rotate-flip.md:** `transpose` values (0=cclock_flip, 1=clock, 2=cclock, 3=clock_flip). 180° = `hflip,vflip`. `rotate` filter for non-90° angles (use `transpose` for 90° increments). Check `rotate` metadata with ffprobe first.

**fade-transitions.md:** `fade=t=in:st=0:d=1` and `afade=t=in:st=0:d=1`. Fade-out needs video duration for `st`. Get duration with ffprobe. Color option: `color=white`. Audio re-encode required for `afade`. Script to auto-compute fade-out start time.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/references/techniques/resize-scale.md skill-repo/ffmpeg/references/techniques/crop-vertical.md skill-repo/ffmpeg/references/techniques/change-speed.md skill-repo/ffmpeg/references/techniques/watermark-overlay.md skill-repo/ffmpeg/references/techniques/burn-subtitles.md skill-repo/ffmpeg/references/techniques/rotate-flip.md skill-repo/ffmpeg/references/techniques/fade-transitions.md
git commit -m "feat(ffmpeg): add transform & filter technique pages"
```

### Task 5: Wiki — Audio Processing (4 pages)

**Files:**
- Create: `skill-repo/ffmpeg/references/techniques/normalize-loudness.md`
- Create: `skill-repo/ffmpeg/references/techniques/remove-silence.md`
- Create: `skill-repo/ffmpeg/references/techniques/denoise-audio.md`
- Create: `skill-repo/ffmpeg/references/techniques/music-ducking.md`

- [ ] **Step 1: Write all 4 technique pages**

**normalize-loudness.md:** Two-pass is mandatory for quality. Pass 1: `-af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null -`. Parse JSON from stderr. Pass 2: feed measured values back. Map `input_i`→`measured_I`, etc. `-ar 48000` to prevent sample rate issues. Targets: -16 LUFS podcast, -14 LUFS YouTube/Spotify, -23 LUFS broadcast. Include the shell script that automates both passes.

**remove-silence.md:** `silenceremove` filter. Use `volumedetect` first to find noise floor. Threshold typically -40 to -30 dB for home studio. `stop_duration=1.0` for podcasts. `start_silence=0.3` for padding. `stop_periods=-1` for middle-of-file removal. Reverse trick for reliable head/tail trimming.

**denoise-audio.md:** `afftdn` for stationary noise (fan, AC). Noise profiling with `asendcmd` at 0.0/0.5s. `nr=10-15` safe range, >20 causes artifacts. `arnndn` for complex noise (wind, room). Model files from GitHub. `mix=0.8` starting point. Chain: afftdn then arnndn for heavy denoising.

**music-ducking.md:** Static mix: `volume=0.15` + `amix` with `normalize=0`. Dynamic ducking: `sidechaincompress` with threshold=0.02, ratio=8, attack=100ms, release=700ms, knee=6. `asplit` to split voice into output + sidechain. `amix normalize=0` is critical. `weights` parameter for simple level control.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/references/techniques/normalize-loudness.md skill-repo/ffmpeg/references/techniques/remove-silence.md skill-repo/ffmpeg/references/techniques/denoise-audio.md skill-repo/ffmpeg/references/techniques/music-ducking.md
git commit -m "feat(ffmpeg): add audio processing technique pages"
```

### Task 6: Wiki — Combine & Assemble (4 pages)

**Files:**
- Create: `skill-repo/ffmpeg/references/techniques/concatenate-clips.md`
- Create: `skill-repo/ffmpeg/references/techniques/mux-audio-video.md`
- Create: `skill-repo/ffmpeg/references/techniques/image-sequence-to-video.md`
- Create: `skill-repo/ffmpeg/references/techniques/complex-filtergraph.md`

- [ ] **Step 1: Write all 4 technique pages**

**concatenate-clips.md:** Demuxer vs filter decision (same codec → demuxer, different → filter). Demuxer: filelist.txt format, `-safe 0`. Filter: `concat=n=3:v=1:a=1`. `-fflags +genpts` for timestamp issues. Add silent audio with `anullsrc` when missing. TS intermediate method (legacy, avoid).

**mux-audio-video.md:** `-map` is essential with multiple inputs. `-c copy` for lossless when codecs match container. `-stream_loop -1 -shortest` for looping music. `-itsoffset` for sync correction (before `-i`). Multi-language tracks with metadata.

**image-sequence-to-video.md:** `-framerate` before `-i` controls read rate. `%04d` pattern, consecutive numbering required. `-pix_fmt yuv420p` mandatory for web. Slideshow: `-framerate 1/5 -r 25`. `hqdn3d` for timelapse flicker. `-start_number` for offset. Glob patterns with `-pattern_type glob`.

**complex-filtergraph.md:** `-filter_complex` required for multi-input. PiP with `overlay=W-w-20:H-h-20`. `hstack`/`vstack` for side-by-side (matching dimensions required). `xstack` for arbitrary grids. `amerge` for channel merging vs `amix` for volume mixing. Every label must be consumed by `-map`.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/references/techniques/concatenate-clips.md skill-repo/ffmpeg/references/techniques/mux-audio-video.md skill-repo/ffmpeg/references/techniques/image-sequence-to-video.md skill-repo/ffmpeg/references/techniques/complex-filtergraph.md
git commit -m "feat(ffmpeg): add combine & assemble technique pages"
```

### Task 7: Wiki — Streaming & Distribution (5 pages)

**Files:**
- Create: `skill-repo/ffmpeg/references/techniques/hls-segments.md`
- Create: `skill-repo/ffmpeg/references/techniques/dash-segments.md`
- Create: `skill-repo/ffmpeg/references/techniques/multi-bitrate.md`
- Create: `skill-repo/ffmpeg/references/techniques/rtmp-restream.md`
- Create: `skill-repo/ffmpeg/references/techniques/fake-live-stream.md`

- [ ] **Step 1: Write all 5 technique pages**

**hls-segments.md:** `-f hls`, `-hls_time 6`, `-hls_playlist_type vod`. Keyframe alignment: `-g 48 -sc_threshold 0 -keyint_min 48`. `-var_stream_map` for multi-quality. mpegts vs fmp4 segments. `-hls_flags independent_segments`. CBR with `nal-hrd=cbr:force-cfr=1`. Live: `-hls_list_size 3 -hls_flags delete_segments`.

**dash-segments.md:** `-f dash`, `-seg_duration 4`. `-adaptation_sets "id=0,streams=v id=1,streams=a"`. `-use_template 1 -use_timeline 1`. CMAF dual-output with `-hls_playlist 1`. Low-latency with `-ldash 1 -streaming 1`. Init segment naming.

**multi-bitrate.md:** `split=3` filter for single-decode multi-encode. Industry bitrate ladder (1080p: 5000k, 720p: 2800k, 480p: 1400k). Capped VBR: maxrate = 1.07× target. `-movflags +faststart` for MP4 outputs. Direct to HLS in one command.

**rtmp-restream.md:** Tee muxer (`-f tee`) for single-encode fan-out. `[f=flv:onfail=ignore]` per destination. `-map 0` required. `-listen 1` for relay mode. Platform URLs (YouTube, Twitch, Facebook RTMPS). Alternative: multiple `-f flv` outputs.

**fake-live-stream.md:** `-re` flag for realtime pacing (must be before `-i`). `-stream_loop -1` for infinite loop. Concat demuxer playlist for reliability. Shell loop for auto-restart. `-tune zerolatency` for low latency. Platform bitrate targets.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/references/techniques/hls-segments.md skill-repo/ffmpeg/references/techniques/dash-segments.md skill-repo/ffmpeg/references/techniques/multi-bitrate.md skill-repo/ffmpeg/references/techniques/rtmp-restream.md skill-repo/ffmpeg/references/techniques/fake-live-stream.md
git commit -m "feat(ffmpeg): add streaming & distribution technique pages"
```

### Task 8: Wiki — Utilities (5 pages)

**Files:**
- Create: `skill-repo/ffmpeg/references/techniques/batch-transcode.md`
- Create: `skill-repo/ffmpeg/references/techniques/ffprobe-validate.md`
- Create: `skill-repo/ffmpeg/references/techniques/rtsp-recording.md`
- Create: `skill-repo/ffmpeg/references/techniques/video-to-gif.md`
- Create: `skill-repo/ffmpeg/references/techniques/screen-capture.md`

- [ ] **Step 1: Write all 5 technique pages**

**batch-transcode.md:** Bash loop with `-nostdin`. Skip-if-exists guard. PowerShell equivalent. GNU parallel for multi-job. Recursive with `find`. NVIDIA GPU batch. Windows CMD batch. Always quote filenames.

**ffprobe-validate.md:** `-v error -print_format json -show_format -show_streams`. Resolution extraction. Codec/bitrate/fps in one jq command. Compliance checks (bitrate threshold, resolution cap). Batch CSV audit. `r_frame_rate` vs `avg_frame_rate`. `-select_streams v:0` for specific stream.

**rtsp-recording.md:** `-rtsp_transport tcp` always. `-use_wallclock_as_timestamps 1`. `-f segment` with strftime naming. MKV for crash resilience. `-segment_atclocktime 1` for aligned boundaries. Systemd service unit. Shell restart loop. 15-minute segments as standard.

**video-to-gif.md:** Two-pass palette approach (palettegen + paletteuse). Pass 1: `palettegen` from scaled/fps-reduced source. Pass 2: `paletteuse` with `-lavfi`. Dithering options (bayer, floyd_steinberg). Scale to 480px or less. 10-15 fps. Shell script wrapping both passes. `stats_mode=diff` for static backgrounds.

**screen-capture.md:** Linux: `x11grab` (X11 only, not Wayland). Windows: `gdigrab` (legacy) vs `ddagrab` (modern, recommended). macOS: `avfoundation`. Audio capture is separate input. Two-pass strategy (lossless then encode). Region capture on all platforms. Window-specific capture. Hardware encoding option per platform.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/references/techniques/batch-transcode.md skill-repo/ffmpeg/references/techniques/ffprobe-validate.md skill-repo/ffmpeg/references/techniques/rtsp-recording.md skill-repo/ffmpeg/references/techniques/video-to-gif.md skill-repo/ffmpeg/references/techniques/screen-capture.md
git commit -m "feat(ffmpeg): add utility technique pages"
```

---

## Task 9: CLI Scaffold — Backend Helpers and App Structure

**Files:**
- Create: `skill-repo/ffmpeg/scripts/ffmpeg_cli.py`

- [ ] **Step 1: Write the CLI scaffold with backend helpers and all 7 command group stubs**

Create `skill-repo/ffmpeg/scripts/ffmpeg_cli.py`:

```python
"""ffmpeg_cli: Agent-native CLI for ffmpeg.

Calls the real ffmpeg/ffprobe binary — does not process media in Python.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="ffmpeg-cli",
    help="Agent-native CLI for ffmpeg.",
    no_args_is_help=True,
)

# Command group sub-apps
convert_app = typer.Typer(help="Format conversion, compression, platform encoding")
extract_app = typer.Typer(help="Trim clips, extract audio, frames, sprites")
transform_app = typer.Typer(help="Resize, crop, speed, watermark, subtitles, rotate, fade")
audio_app = typer.Typer(help="Normalize loudness, denoise, remove silence, music ducking")
combine_app = typer.Typer(help="Concatenate, mux, image sequences, compositing")
stream_app = typer.Typer(help="HLS, DASH, multi-bitrate, RTMP, fake live")
util_app = typer.Typer(help="Batch transcode, probe, screen capture, surveillance")

app.add_typer(convert_app, name="convert")
app.add_typer(extract_app, name="extract")
app.add_typer(transform_app, name="transform")
app.add_typer(audio_app, name="audio")
app.add_typer(combine_app, name="combine")
app.add_typer(stream_app, name="stream")
app.add_typer(util_app, name="util")


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

def find_executable(name: str) -> str:
    """Locate ffmpeg or ffprobe, or exit with install instructions."""
    path = shutil.which(name)
    if path is None:
        typer.echo(
            f"ERROR: {name} not found in PATH.\n"
            "Install from: https://ffmpeg.org/download.html\n"
            "  Windows: winget install ffmpeg\n"
            "  macOS:   brew install ffmpeg\n"
            "  Linux:   apt install ffmpeg",
            err=True,
        )
        raise typer.Exit(code=1)
    return path


def detect_version() -> str:
    """Return the ffmpeg version string."""
    exe = find_executable("ffmpeg")
    result = subprocess.run([exe, "-version"], capture_output=True, text=True)
    first_line = result.stdout.split("\n")[0]
    # "ffmpeg version N.N.N ..." or "ffmpeg version N.N.N-ubuntu..."
    parts = first_line.split()
    if len(parts) >= 3:
        return parts[2]
    return "unknown"


def run_ffmpeg(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run an ffmpeg command. Returns CompletedProcess."""
    exe = find_executable("ffmpeg")
    cmd = [exe] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def run_ffprobe(args: list[str]) -> subprocess.CompletedProcess:
    """Run an ffprobe command. Returns CompletedProcess."""
    exe = find_executable("ffprobe")
    cmd = [exe] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_json(input_path: str) -> dict:
    """Run ffprobe and return parsed JSON."""
    result = run_ffprobe([
        "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        input_path,
    ])
    return json.loads(result.stdout)


def get_duration(input_path: str) -> float:
    """Get duration in seconds from ffprobe."""
    data = probe_json(input_path)
    return float(data.get("format", {}).get("duration", 0))


def report_success(output_path: str) -> None:
    """Report successful output with file size."""
    path = Path(output_path)
    if path.exists():
        size = path.stat().st_size
        if size > 1_000_000:
            size_str = f"{size / 1_000_000:.1f} MB"
        elif size > 1_000:
            size_str = f"{size / 1_000:.1f} KB"
        else:
            size_str = f"{size} bytes"
        typer.echo(f"Output: {output_path} ({size_str})")
    else:
        typer.echo(f"Output: {output_path}")


# ---------------------------------------------------------------------------
# Placeholder: command implementations will be added in Tasks 10-16
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Verify the scaffold runs**

```bash
cd skill-repo/ffmpeg/scripts && uv run ffmpeg_cli.py --help
```

Expected: shows help with convert, extract, transform, audio, combine, stream, util groups.

- [ ] **Step 3: Commit**

```bash
git add skill-repo/ffmpeg/scripts/ffmpeg_cli.py
git commit -m "feat(ffmpeg): add CLI scaffold with backend helpers and command groups"
```

---

## Tasks 10-16: CLI Command Implementation

These 7 tasks are **independent** and can be dispatched in parallel after Task 9 completes. Each task adds commands to one command group in `ffmpeg_cli.py`.

Each command follows the same pattern:
1. Parse Typer arguments
2. Build an ffmpeg argument list
3. Call `run_ffmpeg()` or `run_ffprobe()`
4. Report results with `report_success()`

### Task 10: CLI — Convert Commands

**Files:**
- Modify: `skill-repo/ffmpeg/scripts/ffmpeg_cli.py`

- [ ] **Step 1: Implement convert commands**

Add to `ffmpeg_cli.py` — the `convert_app` group gets these commands:

- `convert format` — video format conversion (transmux or re-encode)
- `convert compress` — CRF-based compression with optional two-pass for target size
- `convert audio` — audio format conversion (MP3/AAC/WAV/FLAC/OGG)
- `convert platform` — platform-specific encoding (YouTube/Twitter/TikTok)
- `convert to-gif` — two-pass palette-optimized GIF
- `convert hwaccel` — hardware-accelerated encoding

Each command should:
- Accept `input` and `output` as positional arguments
- Use the researched ffmpeg flags from the technique pages
- Call `run_ffmpeg()` with the constructed argument list
- Call `report_success()` on completion
- Print the full ffmpeg command to stderr before running (for transparency)

Example implementation for `convert format`:

```python
@convert_app.command("format")
def convert_format(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    codec: str = typer.Option("libx264", "--codec", "-c", help="Video codec"),
    crf: int = typer.Option(23, "--crf", help="Quality (0-51, lower=better)"),
    preset: str = typer.Option("medium", "--preset", help="Encode speed preset"),
    copy: bool = typer.Option(False, "--copy", help="Stream copy (no re-encode)"),
) -> None:
    """Convert video format (MOV/AVI/MKV to MP4)."""
    if copy:
        args = ["-i", input, "-c", "copy", "-movflags", "+faststart", output]
    else:
        args = [
            "-i", input,
            "-c:v", codec, "-crf", str(crf), "-preset", preset,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output,
        ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)
```

Follow this pattern for all 6 commands. Use the technique pages for the correct flags per command. For `to-gif`, implement the two-pass palette approach using a temp file for the palette.

- [ ] **Step 2: Test commands work**

```bash
cd skill-repo/ffmpeg/scripts && uv run ffmpeg_cli.py convert --help
```

Expected: shows all 6 convert subcommands.

- [ ] **Step 3: Commit**

```bash
git add skill-repo/ffmpeg/scripts/ffmpeg_cli.py
git commit -m "feat(ffmpeg): implement convert commands"
```

### Task 11: CLI — Extract Commands

**Files:**
- Modify: `skill-repo/ffmpeg/scripts/ffmpeg_cli.py`

- [ ] **Step 1: Implement extract commands**

Add to `extract_app`:

- `extract clip` — trim by timestamp (`--start`, `--end`, `--duration`, `--copy`)
- `extract audio` — extract audio track (`--format`, `--quality`, `--bitrate`)
- `extract frames` — extract thumbnails (`--at`, `--every`, `--iframes`, `--output-pattern`)
- `extract sprite` — sprite sheet (`--cols`, `--rows`, `--interval`, `--thumb-width`)

Key implementation notes:
- `clip`: put `-ss` before `-i` for fast seeking. Use `-c copy` when `--copy` is set, otherwise re-encode.
- `audio`: use `-vn`. Match codec to output extension. Use `-q:a 2` default for MP3, `-b:a 256k` for AAC.
- `frames`: use `fps=1/N` for interval, `select='eq(pict_type,I)'` for I-frames, `-frames:v 1` for single.
- `sprite`: use `fps=1/N,scale=W:-1,tile=COLSxROWS` with `-frames:v 1`.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/scripts/ffmpeg_cli.py
git commit -m "feat(ffmpeg): implement extract commands"
```

### Task 12: CLI — Transform Commands

**Files:**
- Modify: `skill-repo/ffmpeg/scripts/ffmpeg_cli.py`

- [ ] **Step 1: Implement transform commands**

Add to `transform_app`:

- `transform resize` — scale to target resolution (`--width`, `--height`, `--letterbox`)
- `transform crop` — crop to aspect ratio (`--aspect` 9:16/4:3/1:1, `--pad`)
- `transform speed` — change playback speed (`--factor`, `--interpolate`)
- `transform watermark` — overlay logo (`--logo`, `--position`, `--opacity`, `--scale`)
- `transform subtitles` — burn subtitles (`--srt`, `--font-size`, `--font-name`)
- `transform rotate` — rotate/flip (`--angle` 90/180/270, `--flip` h/v)
- `transform fade` — fade transitions (`--fade-in`, `--fade-out` in seconds)

Key implementation notes:
- `resize`: use `scale=W:-2` (always -2 for even dimensions). Letterbox: `scale=W:H:force_original_aspect_ratio=decrease,pad=W:H:(ow-iw)/2:(oh-ih)/2`.
- `crop`: compute crop expression from aspect ratio. Chain with scale for final resolution.
- `speed`: use `-filter_complex` with `setpts` + `atempo`. Chain `atempo` for >2x.
- `watermark`: use `-filter_complex` with overlay. Accept position as enum.
- `subtitles`: use `subtitles=` filter with optional `force_style=`.
- `rotate`: map angle to `transpose` value. 180° uses `hflip,vflip`.
- `fade`: use `get_duration()` to compute fade-out start time.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/scripts/ffmpeg_cli.py
git commit -m "feat(ffmpeg): implement transform commands"
```

### Task 13: CLI — Audio Commands

**Files:**
- Modify: `skill-repo/ffmpeg/scripts/ffmpeg_cli.py`

- [ ] **Step 1: Implement audio commands**

Add to `audio_app`:

- `audio normalize` — EBU R128 loudness normalization (`--target`, `--tp`)
- `audio silence` — remove silence (`--threshold`, `--min-duration`, `--keep-padding`)
- `audio denoise` — background noise removal (`--method` fft/rnn, `--strength`, `--model`)
- `audio duck` — music ducking (`--voice`, `--music`, `--music-level`, `--dynamic`)

Key implementation notes:
- `normalize`: implement the two-pass approach. Pass 1 runs with `-f null -`, parse JSON from stderr, then run pass 2 with measured values. This is the most complex command.
- `silence`: use `silenceremove` filter with computed threshold.
- `denoise`: use `afftdn` (default) or `arnndn` based on `--method`.
- `duck`: use `sidechaincompress` for dynamic, `volume` + `amix` for static.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/scripts/ffmpeg_cli.py
git commit -m "feat(ffmpeg): implement audio commands"
```

### Task 14: CLI — Combine Commands

**Files:**
- Modify: `skill-repo/ffmpeg/scripts/ffmpeg_cli.py`

- [ ] **Step 1: Implement combine commands**

Add to `combine_app`:

- `combine concat` — concatenate clips (`--files` list, `--filter` for mismatched)
- `combine mux` — mux audio + video (`--video`, `--audio`, `--delay`)
- `combine from-images` — image sequence to video (`--pattern`, `--framerate`)
- `combine composite` — multi-input compositing (`--layout` pip/side-by-side/grid, `--inputs`)

Key implementation notes:
- `concat`: write a temporary filelist.txt, use `-f concat -safe 0`. When `--filter` is set, use the concat filter with `-filter_complex` instead.
- `mux`: use `-map` to select streams explicitly.
- `from-images`: use `-framerate` before `-i`, always add `-pix_fmt yuv420p`.
- `composite`: build `-filter_complex` string based on layout enum.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/scripts/ffmpeg_cli.py
git commit -m "feat(ffmpeg): implement combine commands"
```

### Task 15: CLI — Stream Commands

**Files:**
- Modify: `skill-repo/ffmpeg/scripts/ffmpeg_cli.py`

- [ ] **Step 1: Implement stream commands**

Add to `stream_app`:

- `stream hls` — generate HLS segments (`--segment-duration`, `--qualities`)
- `stream dash` — generate DASH segments (`--segment-duration`, `--qualities`)
- `stream ladder` — multi-bitrate transcode (`--qualities`, `--preset`)
- `stream restream` — RTMP to multiple destinations (`--destinations`)
- `stream fake-live` — pre-recorded as live (`--url`, `--loop`, `--playlist`)

Key implementation notes:
- `hls`: build the full HLS command with `-f hls`, `-var_stream_map`, `-hls_flags independent_segments`.
- `dash`: build DASH command with `-f dash`, `-adaptation_sets`.
- `ladder`: use `split` filter for single-decode multi-encode.
- `restream`: use `-f tee` with `[f=flv:onfail=ignore]` per destination.
- `fake-live`: use `-re` before `-i`, optional `-stream_loop -1`.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/scripts/ffmpeg_cli.py
git commit -m "feat(ffmpeg): implement stream commands"
```

### Task 16: CLI — Util Commands

**Files:**
- Modify: `skill-repo/ffmpeg/scripts/ffmpeg_cli.py`

- [ ] **Step 1: Implement util commands**

Add to `util_app`:

- `util batch` — batch transcode directory (`--input-dir`, `--output-dir`, `--format`)
- `util probe` — probe file with ffprobe (`--json`, `--check`)
- `util record` — screen capture (`--fps`, `--region`, `--audio`)
- `util surveillance` — RTSP recording (`--url`, `--segment-time`, `--output-dir`)

Key implementation notes:
- `batch`: iterate directory, call `run_ffmpeg()` per file, skip existing outputs.
- `probe`: use `probe_json()` helper, format output as Rich table or JSON.
- `record`: detect platform (Windows/macOS/Linux) and use appropriate input device.
- `surveillance`: use `-f segment` with `-strftime 1` and `-rtsp_transport tcp`.

- [ ] **Step 2: Commit**

```bash
git add skill-repo/ffmpeg/scripts/ffmpeg_cli.py
git commit -m "feat(ffmpeg): implement util commands"
```

---

## Task 17: Integration Test

**Files:**
- Create: `tests/test_ffmpeg_skill.py`

- [ ] **Step 1: Write integration tests**

Create `tests/test_ffmpeg_skill.py`:

```python
"""Integration tests for the ffmpeg skill structure and installability."""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from cli_me.main import app as clime_app


runner = CliRunner()
SKILL_DIR = Path(__file__).parent.parent / "skill-repo" / "ffmpeg"


def test_skill_structure_exists():
    """Verify the skill folder has the required structure."""
    assert (SKILL_DIR / "SKILL.md").exists()
    assert (SKILL_DIR / "scripts" / "pyproject.toml").exists()
    assert (SKILL_DIR / "scripts" / "ffmpeg_cli.py").exists()
    assert (SKILL_DIR / "references" / "index.md").exists()
    assert (SKILL_DIR / "references" / "log.md").exists()
    assert (SKILL_DIR / "references" / "gotchas.md").exists()


def test_skill_md_has_frontmatter():
    """Verify SKILL.md has proper YAML frontmatter."""
    content = (SKILL_DIR / "SKILL.md").read_text()
    assert content.startswith("---")
    assert "name: ffmpeg" in content
    assert "description:" in content


def test_all_35_technique_pages_exist():
    """Verify all 35 technique pages were created."""
    techniques = SKILL_DIR / "references" / "techniques"
    expected = [
        "convert-video-format.md", "compress-video.md", "convert-audio-format.md",
        "platform-encoding.md", "hardware-encoding.md", "trim-clip.md",
        "extract-audio.md", "extract-frames.md", "sprite-sheet.md",
        "surveillance-clip.md", "resize-scale.md", "crop-vertical.md",
        "change-speed.md", "watermark-overlay.md", "burn-subtitles.md",
        "rotate-flip.md", "fade-transitions.md", "normalize-loudness.md",
        "remove-silence.md", "denoise-audio.md", "music-ducking.md",
        "concatenate-clips.md", "mux-audio-video.md", "image-sequence-to-video.md",
        "complex-filtergraph.md", "hls-segments.md", "dash-segments.md",
        "multi-bitrate.md", "rtmp-restream.md", "fake-live-stream.md",
        "batch-transcode.md", "ffprobe-validate.md", "rtsp-recording.md",
        "video-to-gif.md", "screen-capture.md",
    ]
    for page in expected:
        assert (techniques / page).exists(), f"Missing technique page: {page}"


def test_technique_pages_have_required_sections():
    """Spot-check that technique pages follow the three-layer structure."""
    techniques = SKILL_DIR / "references" / "techniques"
    for page_path in techniques.glob("*.md"):
        content = page_path.read_text()
        assert "## When to Use" in content, f"{page_path.name} missing 'When to Use'"
        assert "## CLI Commands" in content, f"{page_path.name} missing 'CLI Commands'"
        assert "## Sources" in content, f"{page_path.name} missing 'Sources'"


def test_source_analysis_pages_exist():
    """Verify source analysis pages exist."""
    sa = SKILL_DIR / "references" / "source-analysis"
    assert (sa / "analyzed-version.md").exists()
    assert (sa / "api-surface.md").exists()
    assert (sa / "cli-interface.md").exists()
    assert (sa / "changelog.md").exists()


def test_registry_contains_ffmpeg():
    """Verify ffmpeg is in the registry."""
    registry_path = Path(__file__).parent.parent / "skill-repo" / "registry.json"
    data = json.loads(registry_path.read_text())
    names = [s["name"] for s in data["skills"]]
    assert "ffmpeg" in names


def test_install_ffmpeg_skill(tmp_path):
    """Test installing the ffmpeg skill to a project."""
    result = runner.invoke(clime_app, [
        "install", "ffmpeg", "--project", str(tmp_path)
    ])
    assert result.exit_code == 0
    installed = tmp_path / ".claude" / "skills" / "ffmpeg"
    assert (installed / "SKILL.md").exists()
    assert (installed / "scripts" / "ffmpeg_cli.py").exists()
    assert (installed / "references" / "techniques" / "trim-clip.md").exists()


def test_index_references_all_technique_pages():
    """Verify index.md links to all technique pages."""
    index_content = (SKILL_DIR / "references" / "index.md").read_text()
    techniques = SKILL_DIR / "references" / "techniques"
    for page_path in techniques.glob("*.md"):
        stem = page_path.stem
        assert stem in index_content, f"index.md missing reference to {stem}"
```

- [ ] **Step 2: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: all tests pass, including the new ffmpeg skill tests and the existing cli-me tests.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ffmpeg_skill.py
git commit -m "test(ffmpeg): add integration tests for skill structure and installability"
```

- [ ] **Step 4: Push to remote**

```bash
git push
```

---

## Task Summary

| Task | What | Parallelizable | Dependencies |
|------|------|---------------|-------------|
| 1 | Scaffold (dirs, SKILL.md, registry, source analysis, wiki ops) | No | None |
| 2 | Wiki: Convert & Compress (5 pages) | Yes, with 3-8 | Task 1 |
| 3 | Wiki: Trim & Extract (5 pages) | Yes, with 2,4-8 | Task 1 |
| 4 | Wiki: Transform & Filter (7 pages) | Yes, with 2-3,5-8 | Task 1 |
| 5 | Wiki: Audio Processing (4 pages) | Yes, with 2-4,6-8 | Task 1 |
| 6 | Wiki: Combine & Assemble (4 pages) | Yes, with 2-5,7-8 | Task 1 |
| 7 | Wiki: Streaming & Distribution (5 pages) | Yes, with 2-6,8 | Task 1 |
| 8 | Wiki: Utilities (5 pages) | Yes, with 2-7 | Task 1 |
| 9 | CLI scaffold (backend helpers, group stubs) | No | Task 1 |
| 10 | CLI: Convert commands | Yes, with 11-16 | Task 9 |
| 11 | CLI: Extract commands | Yes, with 10,12-16 | Task 9 |
| 12 | CLI: Transform commands | Yes, with 10-11,13-16 | Task 9 |
| 13 | CLI: Audio commands | Yes, with 10-12,14-16 | Task 9 |
| 14 | CLI: Combine commands | Yes, with 10-13,15-16 | Task 9 |
| 15 | CLI: Stream commands | Yes, with 10-14,16 | Task 9 |
| 16 | CLI: Util commands | Yes, with 10-15 | Task 9 |
| 17 | Integration test + push | No | All |

**Optimal execution:** Task 1 → Tasks 2-8 in parallel + Task 9 → Tasks 10-16 in parallel → Task 17.
