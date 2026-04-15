# Basic Downloading

Download single videos, playlists, and channels with yt-dlp. Covers the most common download scenarios and format selection basics.

## Single Video Download

```bash
# Download with default best quality
yt-dlp "https://www.youtube.com/watch?v=VIDEO_ID"

# Download best video+audio merged (default behavior)
# Equivalent to: -f "bestvideo*+bestaudio/best"
yt-dlp "https://www.youtube.com/watch?v=VIDEO_ID"

# List available formats before downloading
yt-dlp -F "https://www.youtube.com/watch?v=VIDEO_ID"

# Download a specific format by format code
yt-dlp -f 22 "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Playlist Download

```bash
# Download entire playlist
yt-dlp "https://www.youtube.com/playlist?list=PLAYLIST_ID"

# Download specific items from playlist (1st through 5th)
yt-dlp -I 1:5 "https://www.youtube.com/playlist?list=PLAYLIST_ID"

# Download only the video, not the playlist (when URL references both)
yt-dlp --no-playlist "https://www.youtube.com/watch?v=ID&list=PLAYLIST_ID"

# Force playlist download when URL references both
yt-dlp --yes-playlist "https://www.youtube.com/watch?v=ID&list=PLAYLIST_ID"
```

## Channel Download

```bash
# Download all videos from a channel
yt-dlp "https://www.youtube.com/@ChannelName"

# Download channel videos, skipping already-downloaded ones
yt-dlp --download-archive archive.txt "https://www.youtube.com/@ChannelName"
```

## Quick Format Selection

```bash
# Best video + best audio, merged with ffmpeg
yt-dlp -f "bestvideo+bestaudio" "URL"

# Best quality up to 1080p
yt-dlp -S "res:1080" "URL"

# Best mp4 video + m4a audio (no remux needed)
yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]" "URL"

# Audio only (best quality)
yt-dlp -f "bestaudio" "URL"

# Worst quality (save bandwidth)
yt-dlp -f "worst" "URL"
```

## Common Flags

| Flag | Effect |
|------|--------|
| `-F` / `--list-formats` | List all available formats for a URL |
| `-f FORMAT` | Select specific format(s) |
| `-S SORT` | Sort/prefer formats by criteria |
| `--no-playlist` | Download only the video, not the playlist |
| `--yes-playlist` | Download the playlist, not just the video |
| `-I ITEMS` | Select specific playlist items |
| `--download-archive FILE` | Skip already-downloaded videos |
| `-P PATH` | Set download directory |
| `-o TEMPLATE` | Set output filename template |

## Gotchas and Edge Cases

- **URLs with `&` must be quoted.** The shell interprets `&` as a background operator. Always wrap URLs in quotes: `yt-dlp "https://youtube.com/watch?v=X&t=4"`.
- **ffmpeg is required for merging.** YouTube serves high-quality video and audio as separate streams. Without ffmpeg, you only get pre-merged (lower quality) formats or a single stream.
- **Default format changed from youtube-dl.** yt-dlp defaults to `bestvideo*+bestaudio/best` (best video that may include audio, plus best audio). This differs from youtube-dl's `best` (best single file).
- **Some sites need cookies for any download.** If you get HTTP 403 errors, try `--cookies-from-browser chrome`.
- **`-f best` is not the same as the default.** `-f best` selects the best single pre-merged file. The default (`bestvideo*+bestaudio/best`) merges separate streams for higher quality.

## Sources

- [yt-dlp GitHub README](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
- [yt-dlp man page (Arch)](https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en)
- [Arch Wiki - yt-dlp](https://wiki.archlinux.org/title/Yt-dlp)
- [RapidSeedbox yt-dlp Guide](https://www.rapidseedbox.com/blog/yt-dlp-complete-guide)
