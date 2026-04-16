# Post-Processing

SponsorBlock integration, chapter splitting, remuxing, re-encoding, and other ffmpeg-based transformations applied after download.

## SponsorBlock

Automatically mark or remove sponsored segments, intros, outros, and other categories from YouTube videos using the SponsorBlock community database.

### Marking Segments as Chapters

```bash
# Mark sponsor segments as chapters (keeps video intact)
yt-dlp --sponsorblock-mark sponsor "URL"

# Mark multiple categories
yt-dlp --sponsorblock-mark "sponsor,intro,outro" "URL"

# Mark all known categories
yt-dlp --sponsorblock-mark all "URL"

# Mark defaults (all except filler)
yt-dlp --sponsorblock-mark default "URL"
```

### Removing Segments

```bash
# Remove sponsor segments (cuts them from the video)
yt-dlp --sponsorblock-remove sponsor "URL"

# Remove sponsors and intros
yt-dlp --sponsorblock-remove "sponsor,intro" "URL"

# Remove all sponsor categories
yt-dlp --sponsorblock-remove all "URL"

# Remove defaults (all except filler)
yt-dlp --sponsorblock-remove default "URL"

# Mark some, remove others
yt-dlp --sponsorblock-mark intro --sponsorblock-remove sponsor "URL"
```

### SponsorBlock Categories

| Category | Description |
|----------|-------------|
| `sponsor` | Paid promotion |
| `intro` | Intro animation/segment |
| `outro` | Outro/end cards |
| `selfpromo` | Self-promotion (merch, channel plugs) |
| `preview` | Preview/recap of upcoming content |
| `filler` | Tangential content |
| `interaction` | "Like and subscribe" segments |
| `music_offtopic` | Non-music in music videos |
| `poi_highlight` | Highlight/point of interest |
| `chapter` | Community-submitted chapters |
| `all` | All categories |
| `default` | All except filler |

### Custom Chapter Titles

```bash
# Custom title format for SponsorBlock chapters
yt-dlp --sponsorblock-mark all \
  --sponsorblock-chapter-title "[SponsorBlock]: %(category_names)l" "URL"
```

### Disable SponsorBlock

```bash
yt-dlp --no-sponsorblock "URL"
```

## Chapter Splitting

Split a video into separate files based on its internal chapter markers.

```bash
# Split video by chapters
yt-dlp --split-chapters "URL"

# Split with custom output template for chapter files
yt-dlp --split-chapters \
  -o "chapter:%(title)s/%(chapter_number)03d - %(chapter)s.%(ext)s" "URL"

# Split by chapters and remove the original merged file
yt-dlp --split-chapters --no-keep-video "URL"
```

## Removing Chapters by Pattern

```bash
# Remove chapters whose title matches a regex
yt-dlp --remove-chapters "Sponsor" "URL"

# Remove multiple chapter patterns
yt-dlp --remove-chapters "Intro" --remove-chapters "Outro" "URL"

# Force keyframes at cut points (slower, cleaner cuts)
yt-dlp --remove-chapters "Sponsor" --force-keyframes-at-cuts "URL"
```

## Embedding Chapters

```bash
# Embed chapter markers into the file
yt-dlp --embed-chapters "URL"

# Embed metadata (which includes chapters by default)
yt-dlp --embed-metadata "URL"
```

## Remuxing (Container Change, No Re-encoding)

Remuxing changes the container format without re-encoding the streams. Fast and lossless.

```bash
# Remux to MKV
yt-dlp --remux-video mkv "URL"

# Remux to MP4
yt-dlp --remux-video mp4 "URL"

# Remux to MOV
yt-dlp --remux-video mov "URL"
```

Accepted remux formats: `avi`, `flv`, `gif`, `mkv`, `mov`, `mp4`, `webm`, `aac`, `aiff`, `alac`, `flac`, `m4a`, `mka`, `mp3`, `ogg`, `opus`, `vorbis`, `wav`.

## Re-encoding (Transcoding)

Re-encoding transcodes the video/audio streams. Slower than remuxing but allows codec changes.

```bash
# Re-encode to MP4 (typically h264, depends on ffmpeg config)
yt-dlp --recode-video mp4 "URL"

# Re-encode to WebM (typically vp9, depends on ffmpeg config)
yt-dlp --recode-video webm "URL"

# Re-encode to MKV
yt-dlp --recode-video mkv "URL"
```

## Custom FFmpeg Arguments

```bash
# Pass custom arguments to ffmpeg during post-processing
yt-dlp --postprocessor-args "ffmpeg:-vcodec libx264 -crf 18" "URL"

# Custom audio bitrate during extraction
yt-dlp -x --audio-format mp3 \
  --postprocessor-args "ffmpeg:-b:a 256k" "URL"

# Custom video scaling
yt-dlp --postprocessor-args "ffmpeg:-vf scale=1280:720" "URL"

# Pass args to specific post-processor
yt-dlp --postprocessor-args "Merger:-threads 4" "URL"
```

### Named Post-Processors

You can target specific post-processors:

| Name | Description |
|------|-------------|
| `Merger` | Merges video + audio |
| `ExtractAudio` | Audio extraction |
| `VideoRemuxer` | Container remux |
| `VideoConvertor` | Video re-encoding |
| `Metadata` | Metadata embedding |
| `EmbedSubtitle` | Subtitle embedding |
| `EmbedThumbnail` | Thumbnail embedding |
| `SplitChapters` | Chapter splitting |
| `ModifyChapters` | Chapter modification (SponsorBlock, remove-chapters) |

## Download Sections

Download only specific time ranges from a video.

```bash
# Download 30 seconds starting at 1:00
yt-dlp --download-sections "*1:00-1:30" "URL"

# Download from timestamp to end
yt-dlp --download-sections "*1:00-" "URL"

# Download first 2 minutes
yt-dlp --download-sections "*0:00-2:00" "URL"

# Force keyframes for clean cuts
yt-dlp --download-sections "*1:00-1:30" --force-keyframes-at-cuts "URL"
```

## Exec: Run Commands After Download

```bash
# Run a command after each download (filepath is auto-appended)
yt-dlp --exec "echo Downloaded:" "URL"

# Move file to a specific location using output template
yt-dlp --exec "mv %(filepath,_filename|)q /final/location/" "URL"
```

> **Note:** `--exec` commands are OS-specific. Use `mv` on Unix, `move` on Windows.

```bash
# Run after specific post-processing stage
yt-dlp --exec after_move:"echo Final file: %(filepath,_filename|)q" "URL"
```

## Keep or Delete Intermediates

```bash
# Keep the original video after audio extraction
yt-dlp -x --audio-format mp3 -k "URL"
yt-dlp -x --audio-format mp3 --keep-video "URL"

# Delete intermediates (default behavior)
yt-dlp -x --audio-format mp3 --no-keep-video "URL"

# Don't overwrite post-processed files
yt-dlp --no-post-overwrites "URL"
```

## Fixup Options

```bash
# Never fix anything
yt-dlp --fixup never "URL"

# Warn about fixable issues but don't fix
yt-dlp --fixup warn "URL"

# Detect and warn (default)
yt-dlp --fixup detect_or_warn "URL"

# Force all fixups
yt-dlp --fixup force "URL"
```

## Gotchas and Edge Cases

- **`--sponsorblock-remove` requires ffmpeg.** Removing segments uses ffmpeg's concat demuxer with stream copy (no re-encoding), so it's fast and lossless. Cut points may have brief glitches at non-keyframe positions; use `--force-keyframes-at-cuts` for clean cuts (which does re-encode).
- **`--force-keyframes-at-cuts` is slow.** It re-encodes the entire video to ensure clean cuts at chapter/section boundaries. Without it, cuts may have brief glitches at non-keyframe points.
- **SponsorBlock only works for YouTube.** The SponsorBlock API is YouTube-specific. These flags are silently ignored for other sites.
- **`--split-chapters` creates many files.** A 2-hour video with 30 chapters produces 30 files. Use the `chapter:` output template prefix to organize them.
- **Remuxing is fast and lossless. Re-encoding is slow and lossy.** Prefer `--remux-video` over `--recode-video` when you only need to change the container.
- **Post-processor order matters.** yt-dlp runs post-processors in a fixed order. If you need a specific ordering, check issue #10056 on GitHub for workarounds.
- **`--postprocessor-args` syntax changed from youtube-dl.** yt-dlp uses `NAME:ARGS` syntax to target specific post-processors. The old `--postprocessor-args "ARGS"` still works but applies to all ffmpeg invocations.
- **`--download-sections` timestamps use `*` prefix.** The asterisk is required: `"*1:00-2:00"` not `"1:00-2:00"`.
- **`--download-sections` requires ffmpeg.** The section cutting uses ffmpeg for stream manipulation.
- **SponsorBlock is opt-in.** Running `--sponsorblock-remove` or `--sponsorblock-mark` without specifying categories will use default SponsorBlock categories. Running neither flag downloads the video with no SponsorBlock action.
- **`process chapters` with no action flags is a no-op download.** Calling `process chapters URL` without `--split` or `--remove` will download the video with no chapter processing (exits 0, may print a warning). Always pass at least one of `--split` or `--remove <pattern>`.
- **`process embed` with no embed flags is a no-op download.** Calling `process embed URL` without any embed flags (`--metadata`, `--thumbnail`, `--subs`, `--chapters`) will download the video with no embedding (exits 0, warning only). Always specify what to embed.

## Sources

- [yt-dlp GitHub README](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp man page (Arch)](https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en)
- [SponsorBlock Integration - yt-dlp Mintlify](https://mintlify.wiki/yt-dlp/yt-dlp/guides/sponsorblock)
- [yt-dlp cheat sheet - Ditig](https://www.ditig.com/yt-dlp-cheat-sheet)
- [Post-processor order issue #10056](https://github.com/yt-dlp/yt-dlp/issues/10056)

## Learned from Usage

(No usage notes yet.)
