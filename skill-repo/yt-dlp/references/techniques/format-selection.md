# Format Selection

The `-f` / `--format` flag controls which video and audio streams yt-dlp downloads. The `-S` / `--format-sort` flag controls how "best" is defined.

## Format Specifier Types

| Specifier | Meaning |
|-----------|---------|
| `b` / `best` | Best single file with both video and audio |
| `bv` / `bestvideo` | Best video-only stream |
| `ba` / `bestaudio` | Best audio-only stream |
| `bv*` / `bestvideo*` | Best stream containing video (may also have audio) |
| `ba*` / `bestaudio*` | Best stream containing audio (may also have video) |
| `w` / `worst` | Worst single file |
| `wv` / `worstvideo` | Worst video-only stream |
| `wa` / `worstaudio` | Worst audio-only stream |
| `all` | Download all formats separately |

The default is `bv*+ba/b` -- best video (possibly with audio) plus best audio, falling back to best single file.

## Combining Formats

```bash
# Merge video + audio (requires ffmpeg)
yt-dlp -f "bestvideo+bestaudio" "URL"

# Fallback chain: try format 22, then 18, then 17
yt-dlp -f "22/18/17" "URL"

# Download multiple formats as separate files
yt-dlp -f "22,17,18" "URL"

# Merge with + , fallback with /
yt-dlp -f "bestvideo+bestaudio/best" "URL"
```

## Filter Expressions

Filter available formats using bracket syntax `[key operator value]`.

**Comparison operators:** `<`, `<=`, `>`, `>=`, `=`, `!=`
**String operators:** `^=` (starts with), `$=` (ends with), `*=` (contains), `~=` (regex)
**Negate:** prefix with `!` (e.g., `[!vcodec=none]`)
**Unknown values:** append `?` to include formats where the field is unknown (e.g., `[height<=?720]`)

```bash
# Best mp4 up to 720p
yt-dlp -f "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]" "URL"

# Best format under 50MB
yt-dlp -f "best[filesize<50M]" "URL"

# Best video that is NOT vp9 codec
yt-dlp -f "bestvideo[vcodec!=vp9]+bestaudio" "URL"

# Group filter: best mp4 or webm under 480p
yt-dlp -f "(mp4,webm)[height<480]" "URL"

# Video with specific codec containing a substring
yt-dlp -f "bestvideo[vcodec*=avc]+bestaudio" "URL"
```

## Format Sorting (-S)

The `-S` flag changes what "best" means. By default, yt-dlp prefers higher resolution, then better codec, then higher bitrate.

```bash
# Prefer 1080p (closest to, not exceeding)
yt-dlp -S "res:1080" "URL"

# Prefer h264 codec
yt-dlp -S "codec:h264" "URL"

# Prefer 720p, then fps, then codec quality
yt-dlp -S "res:720,fps,codec" "URL"

# Prefer mp4 extension
yt-dlp -S "ext:mp4:m4a" "URL"

# Prefer h264 video and m4a audio
yt-dlp -S "codec:avc:m4a" "URL"

# Smallest file first (+ reverses sort to prefer lower/smaller values)
yt-dlp -S "+size" "URL"
```

### Force Sort Override

```bash
# Override default sort entirely (force your sort to take full precedence)
yt-dlp -S "res:720,fps" --format-sort-force "URL"
```

Without `--format-sort-force`, yt-dlp applies your sort on top of its defaults. With it, only your specified fields matter.

## Default Codec Preferences

**Video codecs (best to worst):** av01 > vp9.2 > vp9 > h265 > h264 > vp8 > h263 > theora > other

**Audio codecs (best to worst):** flac/alac > wav/aiff > opus > vorbis > aac > mp4a > mp3 > ac4 > eac3 > ac3 > dts > other

**Video extensions:** mp4 > mov > webm > flv > other

**Audio extensions:** m4a > aac > mp3 > ogg > opus > webm > other

## Merge Output Format

```bash
# Force merged output to mkv
yt-dlp -f "bestvideo+bestaudio" --merge-output-format mkv "URL"

# Force merged output to mp4
yt-dlp -f "bestvideo+bestaudio" --merge-output-format mp4 "URL"
```

Accepted merge formats: `avi`, `flv`, `mkv`, `mov`, `mp4`, `webm`.

## Gotchas and Edge Cases

- **`-f best` is NOT the default.** The default is `bv*+ba/b`. Using `-f best` gets the best pre-merged file, which is often lower quality than merging separate streams.
- **Merging requires ffmpeg.** Without it, yt-dlp falls back to the best single-file format.
- **Numeric fields use numeric comparison.** `[height<=720]` compares numerically. Use `?` suffix (e.g., `[filesize<=?50M]`) when values might be missing — without it, formats with unknown values are excluded.
- **Codec filters use internal names.** Use `-F` to see what codec names a site reports (e.g., `avc1.64001F` for h264 on YouTube).
- **Format codes are site-specific.** Format code `22` means 720p mp4 on YouTube, but codes differ across sites. Use `-F` to check.
- **`-S` and `-f` can be combined.** `-S` controls ranking within the pool; `-f` controls which formats are eligible.

## Sources

- [yt-dlp GitHub README](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp man page (Arch)](https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en)
- [Format Selection and Sorting - DeepWiki](https://deepwiki.com/yt-dlp/yt-dlp/2.3-format-selection-and-sorting)
- [Format Selection - yt-dlp Mintlify](https://mintlify.wiki/yt-dlp/yt-dlp/core-concepts/format-selection)
- [yt-dlp cheat sheet - Ditig](https://www.ditig.com/yt-dlp-cheat-sheet)

## Learned from Usage

(No usage notes yet.)
