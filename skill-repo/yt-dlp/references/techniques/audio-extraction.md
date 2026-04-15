# Audio Extraction

Extract audio from videos, convert to various formats, and control quality/bitrate settings.

## Basic Audio Extraction

```bash
# Extract audio in best available format
yt-dlp -x "URL"

# Extract and convert to mp3
yt-dlp -x --audio-format mp3 "URL"

# Extract to mp3 with best quality (VBR 0 = ~256-320 kbps)
yt-dlp -x --audio-format mp3 --audio-quality 0 "URL"

# Extract to opus
yt-dlp -x --audio-format opus "URL"

# Extract to FLAC (lossless)
yt-dlp -x --audio-format flac "URL"

# Extract to WAV (uncompressed)
yt-dlp -x --audio-format wav "URL"

# Extract to m4a/AAC
yt-dlp -x --audio-format m4a "URL"

# Extract to vorbis (ogg container)
yt-dlp -x --audio-format vorbis "URL"

# Extract to ALAC (Apple Lossless)
yt-dlp -x --audio-format alac "URL"
```

## Supported Audio Formats

| Format | Type | Notes |
|--------|------|-------|
| `best` | Default | Keep original format, no conversion |
| `mp3` | Lossy | Most compatible, widely supported |
| `opus` | Lossy | Better quality per bitrate than mp3 |
| `vorbis` | Lossy | Open format, ogg container |
| `aac` | Lossy | Good compatibility, Apple/mobile |
| `m4a` | Lossy | AAC in MP4 container |
| `flac` | Lossless | Lossless compression |
| `alac` | Lossless | Apple Lossless |
| `wav` | Uncompressed | Large files, no quality loss |

## Quality and Bitrate Control

The `--audio-quality` flag accepts VBR quality levels (0-10) or a specific bitrate.

```bash
# VBR quality 0 (best, ~256-320 kbps for mp3)
yt-dlp -x --audio-format mp3 --audio-quality 0 "URL"

# VBR quality 5 (default, ~128 kbps for mp3)
yt-dlp -x --audio-format mp3 --audio-quality 5 "URL"

# VBR quality 10 (worst)
yt-dlp -x --audio-format mp3 --audio-quality 10 "URL"

# Fixed bitrate: 192 kbps
yt-dlp -x --audio-format mp3 --audio-quality 192K "URL"

# Fixed bitrate: 320 kbps
yt-dlp -x --audio-format mp3 --audio-quality 320K "URL"

# Fixed bitrate: 128 kbps
yt-dlp -x --audio-format mp3 --audio-quality 128K "URL"
```

## Download Audio-Only Without Conversion

```bash
# Download best audio stream without converting (no -x needed)
yt-dlp -f "bestaudio" "URL"

# Download best audio, prefer opus codec
yt-dlp -f "bestaudio" -S "codec:opus" "URL"

# Download best audio, prefer m4a extension
yt-dlp -f "bestaudio[ext=m4a]" "URL"

# Download best audio, prefer webm/opus
yt-dlp -f "bestaudio[ext=webm]" "URL"
```

## Audio with Metadata

```bash
# Extract mp3 with embedded metadata and thumbnail
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  --embed-metadata --embed-thumbnail "URL"

# Full music download: mp3 with metadata, thumbnail, and lyrics
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  --embed-metadata --embed-thumbnail \
  --write-subs --sub-langs "en" --embed-subs "URL"

# FLAC with all metadata
yt-dlp -x --audio-format flac \
  --embed-metadata --embed-thumbnail "URL"
```

## Playlist Audio Extraction

```bash
# Download entire playlist as mp3
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  -o "%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s" \
  "PLAYLIST_URL"

# Download playlist as mp3, skip already-downloaded
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  --download-archive audio-archive.txt \
  "PLAYLIST_URL"
```

## Default Codec Quality Hierarchy

yt-dlp internally ranks audio codecs in this order when choosing "best":

flac/alac > wav/aiff > opus > vorbis > aac > mp4a > mp3 > ac4 > eac3 > ac3 > dts > other

## Gotchas and Edge Cases

- **`-x` requires ffmpeg.** Without ffmpeg, audio extraction and format conversion will fail.
- **`--audio-quality` default is 5, not 0.** The default quality level of 5 produces medium-quality output (~128 kbps for mp3). Use `--audio-quality 0` for best quality.
- **Converting to FLAC from a lossy source is pointless.** If YouTube serves opus at 128 kbps, converting to FLAC just makes a larger file with no quality improvement. FLAC only helps if the source is already lossless.
- **`-f bestaudio` and `-x` are different.** `-f bestaudio` downloads the best audio stream as-is. `-x` extracts audio from whatever is downloaded and optionally converts it. You can combine them: `-f bestaudio -x --audio-format mp3`.
- **YouTube's best audio is typically opus at 128-251 kbps.** You cannot extract higher quality than the source provides. Converting to 320 kbps mp3 will not improve quality.
- **Thumbnail embedding in mp3 requires mutagen or AtomicParsley.** Install one of these Python packages for reliable thumbnail embedding.
- **m4a is generally the best choice for Apple ecosystems.** It's natively supported on iOS/macOS without transcoding.
- **opus offers better quality per bitrate than mp3.** At 128 kbps, opus sounds noticeably better than mp3 at the same bitrate.

## Sources

- [yt-dlp GitHub README](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp man page (Arch)](https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en)
- [Extract High-Quality Audio Only with yt-dlp - GoProxy](https://www.goproxy.com/blog/yt-dlp-audio-only/)
- [yt-dlp audio quality issue #9690](https://github.com/yt-dlp/yt-dlp/issues/9690)
- [yt-dlp audio quality default issue #13807](https://github.com/yt-dlp/yt-dlp/issues/13807)
- [Spacebar: How to download audio-only with yt-dlp](https://www.spacebar.news/how-to-download-audio-only-media-files-with-yt-dlp/)
