# Metadata and Subtitles

Embed metadata, thumbnails, and subtitles into downloaded files. Write sidecar files for info JSON, descriptions, and subtitle tracks.

## Embedding Metadata

```bash
# Embed metadata (title, artist, date, description, etc.)
yt-dlp --embed-metadata "URL"

# Embed metadata + chapters (--embed-metadata includes chapters by default)
yt-dlp --embed-metadata "URL"

# Embed metadata but NOT chapters
yt-dlp --embed-metadata --no-embed-chapters "URL"

# Embed metadata but NOT info JSON
yt-dlp --embed-metadata --no-embed-info-json "URL"
```

## Embedding Thumbnails

```bash
# Embed thumbnail as cover art
yt-dlp --embed-thumbnail "URL"

# Embed thumbnail in audio file (mp3/m4a)
yt-dlp -x --audio-format mp3 --embed-thumbnail "URL"

# Write thumbnail to separate file
yt-dlp --write-thumbnail "URL"

# Write all available thumbnails
yt-dlp --write-all-thumbnails "URL"

# Convert thumbnail format before embedding
yt-dlp --embed-thumbnail --convert-thumbnails png "URL"
```

## Subtitles

### Downloading Subtitles

```bash
# Download subtitles (manual/uploaded subtitles only)
yt-dlp --write-subs "URL"

# Download auto-generated subtitles
yt-dlp --write-auto-subs "URL"

# Download both manual and auto-generated
yt-dlp --write-subs --write-auto-subs "URL"

# List available subtitle languages
yt-dlp --list-subs "URL"
```

### Selecting Subtitle Languages

```bash
# Download English subtitles
yt-dlp --write-subs --sub-langs en "URL"

# Download English and Spanish
yt-dlp --write-subs --sub-langs "en,es" "URL"

# Download all subtitles
yt-dlp --write-subs --sub-langs all "URL"

# Download all subtitles except live_chat
yt-dlp --write-subs --sub-langs "all,-live_chat" "URL"

# Regex: all English variants (en, en-US, en-GB, etc.)
yt-dlp --write-subs --sub-langs "en.*" "URL"

# Regex: English variants + Japanese
yt-dlp --write-subs --sub-langs "en.*,ja" "URL"
```

### Embedding Subtitles

```bash
# Embed subtitles into video file (mp4, webm, mkv only)
yt-dlp --write-subs --sub-langs en --embed-subs "URL"

# Embed all subtitles
yt-dlp --write-subs --sub-langs all --embed-subs "URL"

# Embed auto-generated subtitles
yt-dlp --write-auto-subs --sub-langs en --embed-subs "URL"
```

### Subtitle Format Conversion

```bash
# Convert subtitles to SRT
yt-dlp --write-subs --sub-langs en --convert-subs srt "URL"

# Convert to VTT
yt-dlp --write-subs --sub-langs en --convert-subs vtt "URL"

# Convert to ASS
yt-dlp --write-subs --sub-langs en --convert-subs ass "URL"

# Convert to LRC (lyrics format)
yt-dlp --write-subs --sub-langs en --convert-subs lrc "URL"
```

Supported subtitle conversion formats: `ass`, `lrc`, `srt`, `vtt`.

## Writing Sidecar Files

```bash
# Write video info as JSON
yt-dlp --write-info-json "URL"

# Write video description to .description file
yt-dlp --write-description "URL"

# Write thumbnail image
yt-dlp --write-thumbnail "URL"

# Write comments to info JSON
yt-dlp --write-comments "URL"

# Write everything: subs, info JSON, description, thumbnail
yt-dlp --write-subs --write-info-json --write-description --write-thumbnail "URL"
```

## Metadata Parsing and Replacement

```bash
# Parse title into metadata fields (regex capture groups)
yt-dlp --parse-metadata "title:%(artist)s - %(track)s" "URL"

# Parse description for specific metadata
yt-dlp --parse-metadata "description:(?P<meta_comment>.*)" "URL"

# Replace text in metadata fields using regex
yt-dlp --replace-in-metadata "title" "\s+" "_" "URL"

# Set a fixed metadata value
yt-dlp --parse-metadata ":(?P<meta_genre>Music)" "URL"
```

## The Kitchen Sink: Embed Everything

```bash
# Embed all available metadata, thumbnail, subtitles, and chapters
yt-dlp \
  --embed-metadata \
  --embed-thumbnail \
  --embed-subs \
  --embed-chapters \
  --write-subs --sub-langs "all,-live_chat" \
  "URL"

# Same but also write sidecar files
yt-dlp \
  --embed-metadata \
  --embed-thumbnail \
  --embed-subs \
  --embed-chapters \
  --write-subs --sub-langs "all,-live_chat" \
  --write-info-json \
  --write-description \
  --write-thumbnail \
  "URL"
```

## Embed Info JSON in MKV

```bash
# Attach full info JSON as MKV attachment
yt-dlp --embed-info-json --merge-output-format mkv "URL"
```

This only works with MKV/MKA containers.

## Common Flags Reference

| Flag | Effect |
|------|--------|
| `--embed-metadata` | Embed title, artist, date, etc. Also embeds chapters and infojson by default |
| `--embed-thumbnail` | Embed thumbnail as cover art |
| `--embed-subs` | Embed subtitle tracks into video container |
| `--embed-chapters` | Embed chapter markers |
| `--embed-info-json` | Attach info JSON to mkv/mka |
| `--write-subs` | Write subtitle files alongside video |
| `--write-auto-subs` | Write auto-generated subtitle files |
| `--sub-langs LANGS` | Subtitle language selection (comma-separated, supports regex) |
| `--convert-subs FORMAT` | Convert subtitle format (ass, lrc, srt, vtt) |
| `--write-info-json` | Write .info.json sidecar file |
| `--write-description` | Write .description sidecar file |
| `--write-thumbnail` | Write thumbnail image file |
| `--write-comments` | Include comments in info JSON |
| `--parse-metadata FROM:TO` | Parse/transform metadata fields |
| `--replace-in-metadata FIELDS REGEX REPLACE` | Regex replace in metadata |
| `--list-subs` | List available subtitle languages |

## Gotchas and Edge Cases

- **`--embed-subs` only works with mp4, webm, and mkv containers.** Other formats silently skip subtitle embedding.
- **`--embed-metadata` also embeds chapters and infojson by default.** Use `--no-embed-chapters` or `--no-embed-info-json` to disable.
- **`--embed-thumbnail` in mp3 requires mutagen or AtomicParsley.** Without these dependencies, thumbnail embedding may fail silently for mp3 files.
- **WebP thumbnails can cause issues.** Some players don't support WebP cover art. Use `--convert-thumbnails jpg` or `--convert-thumbnails png` to convert before embedding.
- **`--sub-langs` accepts regex patterns.** `en.*` matches en, en-US, en-GB, etc. Always quote the value to prevent shell glob expansion.
- **`--write-auto-subs` downloads YouTube's auto-generated subtitles.** These are separate from manually uploaded subtitles (`--write-subs`). You need both flags to get both types.
- **`live_chat` is a subtitle language on YouTube.** Exclude it with `--sub-langs "all,-live_chat"` to avoid downloading the chat replay as a subtitle file.
- **Info JSON files can be large.** With `--write-comments`, info JSON files can be tens of megabytes for popular videos with many comments.

## Sources

- [yt-dlp GitHub README](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp man page (Arch)](https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en)
- [yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
- [Embed all subtitles, thumbnails, metadata - issue #3316](https://github.com/yt-dlp/yt-dlp/issues/3316)
- [yt-dlp cheat sheet - Ditig](https://www.ditig.com/yt-dlp-cheat-sheet)
