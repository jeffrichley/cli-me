# ffmpeg Skill Design

**Date:** 2026-04-15
**Status:** Draft
**Author:** Jeff Richley + Claude

---

## Overview

The ffmpeg skill is the first skill built for cli-me. It wraps ffmpeg and ffprobe
with a Typer CLI that provides intent-based commands for 35 common workflows,
backed by a self-evolving wiki of technique pages with real commands, best practices,
and source attribution.

ffmpeg is the ideal first skill because: everyone needs it, the flag syntax is
notoriously hard to remember, and the wiki pattern proves its value immediately —
every workflow gets documented with the *why*, not just the *what*.

## Principles

1. **Call the real ffmpeg.** Every command shells out to ffmpeg or ffprobe. We never
   decode, encode, or process media in Python.
2. **Intent-based commands.** Instead of remembering flag combinations, the user says
   `ffmpeg-cli convert to-gif` or `ffmpeg-cli audio normalize`. The CLI builds the
   correct ffmpeg command.
3. **Wiki is the knowledge layer.** The 35 technique pages are the real value. The CLI
   is the convenience layer. An agent can use either — read the wiki for understanding,
   call the CLI for execution.
4. **Self-evolving.** Every use writes back what worked and what didn't.

---

## Skill Structure

```
skill-repo/ffmpeg/
├── SKILL.md
├── scripts/
│   ├── pyproject.toml
│   └── ffmpeg_cli.py
└── references/
    ├── index.md
    ├── log.md
    ├── gotchas.md
    ├── source-analysis/
    │   ├── analyzed-version.md
    │   ├── api-surface.md
    │   ├── cli-interface.md
    │   └── changelog.md
    └── techniques/
        ├── convert-video-format.md
        ├── compress-video.md
        ├── convert-audio-format.md
        ├── platform-encoding.md
        ├── hardware-encoding.md
        ├── trim-clip.md
        ├── extract-audio.md
        ├── extract-frames.md
        ├── sprite-sheet.md
        ├── surveillance-clip.md
        ├── resize-scale.md
        ├── crop-vertical.md
        ├── change-speed.md
        ├── watermark-overlay.md
        ├── burn-subtitles.md
        ├── rotate-flip.md
        ├── fade-transitions.md
        ├── normalize-loudness.md
        ├── remove-silence.md
        ├── denoise-audio.md
        ├── music-ducking.md
        ├── concatenate-clips.md
        ├── mux-audio-video.md
        ├── image-sequence-to-video.md
        ├── complex-filtergraph.md
        ├── hls-segments.md
        ├── dash-segments.md
        ├── multi-bitrate.md
        ├── rtmp-restream.md
        ├── fake-live-stream.md
        ├── batch-transcode.md
        ├── ffprobe-validate.md
        ├── rtsp-recording.md
        ├── video-to-gif.md
        └── screen-capture.md
```

---

## SKILL.md

The SKILL.md triggers on: "ffmpeg", "convert video", "compress video", "extract audio",
"trim video", "clip video", "resize video", "add subtitles", "remove background noise",
"normalize audio", "create gif", "stream video", "HLS", "DASH", "RTMP", "concatenate",
"merge videos", "watermark", "timelapse", "slow motion", "screen capture", "ffprobe",
"video to gif", "podcast audio".

The body teaches Claude:
1. How to invoke the CLI: `uv run scripts/ffmpeg_cli.py <group> <command> [options]`
2. Where to find technique docs: `references/techniques/`
3. How to read source analysis: `references/source-analysis/`
4. Write-back instructions (standard cli-me section)

---

## Typer CLI Command Groups

The CLI is organized into 7 groups with commands that map to the 35 workflows.
Each command constructs and executes the correct ffmpeg/ffprobe invocation.

### `convert` — Format Conversion & Compression

| Command | Workflow | Key Flags |
|---------|----------|-----------|
| `convert format` | Convert video format (MOV/AVI/MKV → MP4) | `--codec`, `--crf`, `--copy` (transmux) |
| `convert compress` | Compress to target quality | `--crf`, `--preset`, `--target-size` (two-pass) |
| `convert audio` | Convert audio format | `--codec`, `--quality`, `--bitrate` |
| `convert platform` | Encode for YouTube/Twitter/TikTok | `--platform` (youtube\|twitter\|tiktok) |
| `convert to-gif` | Video to palette-optimized GIF | `--fps`, `--width`, `--dither` |
| `convert hwaccel` | Hardware-accelerated encode | `--encoder` (nvenc\|vaapi\|videotoolbox), `--quality` |

### `extract` — Trim & Extract

| Command | Workflow | Key Flags |
|---------|----------|-----------|
| `extract clip` | Trim by timestamp | `--start`, `--end`, `--duration`, `--copy` |
| `extract audio` | Extract audio track | `--format` (mp3\|aac\|wav\|flac), `--quality` |
| `extract frames` | Extract frame(s) as images | `--at` (timestamp), `--every` (interval), `--iframes` |
| `extract sprite` | Thumbnail sprite sheet | `--cols`, `--rows`, `--interval` |

### `transform` — Visual Transforms & Filters

| Command | Workflow | Key Flags |
|---------|----------|-----------|
| `transform resize` | Resize/scale | `--width`, `--height`, `--letterbox` |
| `transform crop` | Crop (landscape→vertical) | `--aspect` (9:16\|4:3\|1:1), `--pad` |
| `transform speed` | Change playback speed | `--factor` (0.5=slow, 2.0=fast), `--interpolate` |
| `transform watermark` | Add logo/watermark overlay | `--logo`, `--position` (tl\|tr\|bl\|br\|center), `--opacity` |
| `transform subtitles` | Burn subtitles into video | `--srt`, `--font-size`, `--style` |
| `transform rotate` | Rotate/flip | `--angle` (90\|180\|270), `--flip` (h\|v) |
| `transform fade` | Fade in/out | `--fade-in`, `--fade-out` (duration in seconds) |

### `audio` — Audio Processing

| Command | Workflow | Key Flags |
|---------|----------|-----------|
| `audio normalize` | EBU R128 loudness normalization | `--target` (-16\|-14\|-23 LUFS), `--two-pass` |
| `audio silence` | Remove silence/dead air | `--threshold`, `--min-duration`, `--keep-padding` |
| `audio denoise` | Remove background noise | `--method` (fft\|rnn), `--strength`, `--model` |
| `audio duck` | Mix music under voiceover | `--voice`, `--music`, `--music-level`, `--dynamic` |

### `combine` — Combine & Assemble

| Command | Workflow | Key Flags |
|---------|----------|-----------|
| `combine concat` | Concatenate clips | `--files` (list), `--filter` (for mismatched) |
| `combine mux` | Mux audio + video | `--video`, `--audio`, `--delay` |
| `combine from-images` | Image sequence to video | `--pattern`, `--framerate`, `--codec` |
| `combine composite` | Multi-input compositing | `--layout` (pip\|side-by-side\|grid), `--inputs` |

### `stream` — Streaming & Distribution

| Command | Workflow | Key Flags |
|---------|----------|-----------|
| `stream hls` | Generate HLS segments | `--segment-duration`, `--qualities`, `--segment-type` |
| `stream dash` | Generate DASH segments | `--segment-duration`, `--qualities` |
| `stream ladder` | Multi-bitrate transcode | `--qualities` (1080p,720p,480p), `--preset` |
| `stream restream` | RTMP to multiple destinations | `--destinations` (list of rtmp:// URLs) |
| `stream fake-live` | Stream pre-recorded as live | `--url`, `--loop`, `--playlist` |

### `util` — Utilities

| Command | Workflow | Key Flags |
|---------|----------|-----------|
| `util batch` | Batch transcode directory | `--input-dir`, `--output-dir`, `--format`, `--parallel` |
| `util probe` | Probe/validate file | `--json`, `--check` (codec\|bitrate\|resolution) |
| `util record` | Screen capture | `--fps`, `--region`, `--audio` |
| `util surveillance` | RTSP recording | `--url`, `--segment-time`, `--output-dir` |

---

## Backend Pattern

The CLI backend is pure subprocess. Every command:

1. Calls `find_executable("ffmpeg")` or `find_executable("ffprobe")`
2. Builds an argument list from the Typer parameters
3. Runs `subprocess.run()` with `capture_output=True`
4. Reports results (success, output path, file size) or errors

```python
def find_executable(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        typer.echo(f"ERROR: {name} not found. Install from https://ffmpeg.org/download.html", err=True)
        raise typer.Exit(code=1)
    return path

def detect_version() -> tuple[int, ...]:
    exe = find_executable("ffmpeg")
    result = subprocess.run([exe, "-version"], capture_output=True, text=True)
    # Parse "ffmpeg version N.N.N" from first line
    ...
```

No version-specific branching is needed for the initial implementation. ffmpeg's
CLI interface is stable across versions. If version-specific behavior surfaces during
use, the wiki's `gotchas.md` and `changelog.md` will capture it, and branching can
be added later.

---

## Wiki Content

The 35 technique pages were researched by 7 parallel agents covering:

1. **Convert & Compress** (5 pages) — format conversion, CRF tuning, audio conversion,
   platform-specific encoding (YouTube/Twitter/TikTok specs), hardware acceleration
   (NVENC/VAAPI/VideoToolbox)
2. **Trim & Extract** (5 pages) — timestamp trimming (input vs output seeking, stream
   copy vs re-encode), audio extraction, frame extraction (thumbnail filter, fps filter,
   I-frame selection), sprite sheets (tile filter), surveillance clip extraction
3. **Transform & Filter** (7 pages) — resize/scale (-2 for even dimensions), crop
   (landscape to 9:16), speed change (setpts + atempo, minterpolate), watermark overlay,
   subtitle burn-in (SRT/ASS, force_style, Windows path escaping), rotate/flip
   (transpose values), fade transitions
4. **Audio Processing** (4 pages) — EBU R128 two-pass loudness normalization, silence
   removal (silenceremove filter, threshold selection), denoising (afftdn with noise
   profiling, arnndn neural network), music ducking (sidechaincompress)
5. **Combine & Assemble** (4 pages) — concat demuxer vs filter (when to use which),
   muxing separate tracks (-map, -stream_loop, -itsoffset), image sequence to video
   (-framerate before -i), complex filtergraph compositing (overlay, hstack, vstack,
   xstack, amerge)
6. **Streaming & Distribution** (5 pages) — HLS adaptive (keyframe alignment,
   -sc_threshold 0, var_stream_map, mpegts vs fmp4), MPEG-DASH (adaptation sets,
   SegmentTemplate, CMAF dual-output), multi-bitrate ladder (split filter, capped
   VBR), RTMP restreaming (tee muxer, onfail=ignore), fake live (concat demuxer
   playlist, -re flag, shell loop restart)
7. **Batch, Probe & Special** (5 pages) — batch transcode (bash/PowerShell loops,
   -nostdin, parallel), ffprobe (JSON output, jq parsing, compliance checks), RTSP
   recording (TCP transport, segment muxer, strftime, systemd), GIF (two-pass
   palettegen + paletteuse), screen capture (x11grab/gdigrab/ddagrab/avfoundation,
   all three platforms)

Each page follows the three-layer structure:
- **Domain knowledge** — what it is, when to use it, parameters, common mistakes
- **Executable knowledge** — real ffmpeg commands with multiple variants
- **Provenance** — source URLs for attribution and deeper reading

---

## Registry Entry

```json
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
```

---

## Implementation Order

1. **Wiki first.** Write all 35 technique pages + source analysis + operational files.
   This is the bulk of the value and doesn't require ffmpeg to be installed.
2. **SKILL.md.** Write the skill trigger and instructions.
3. **Typer CLI scaffold.** Create `scripts/pyproject.toml` and `ffmpeg_cli.py` with
   the 7 command groups and basic commands.
4. **Implement commands.** Start with the highest-impact group (`convert`), then
   `extract`, `transform`, `audio`, `combine`, `util`, `stream`.
5. **Registry entry.** Add to `skill-repo/registry.json`.
6. **Test.** Verify commands work against a real ffmpeg install.

---

## What This Skill Is Not

- **Not an ffmpeg reimplementation.** The CLI calls ffmpeg. It doesn't decode or encode.
- **Not a GUI.** No interactive mode, no menus. Commands are one-shot.
- **Not exhaustive.** 35 workflows cover the common cases. The wiki grows to cover more
  as agents use it and write back what they learn.
- **Not a replacement for reading the wiki.** The CLI is convenience. The wiki is the
  knowledge. An agent should read the technique page before using a command for the
  first time.
