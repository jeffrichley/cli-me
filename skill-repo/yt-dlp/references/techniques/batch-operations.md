# Batch Operations

Batch files, config files, download archives, and strategies for large-scale incremental downloads.

## Batch Files

Download multiple URLs from a text file, one URL per line.

```bash
# Download all URLs from a file
yt-dlp -a urls.txt  # add other options as needed

# Equivalent long form
yt-dlp --batch-file urls.txt

# Read URLs from stdin
echo "https://youtube.com/watch?v=ID1" | yt-dlp -a -
```

### Batch File Format

```
# This is a comment (lines starting with #, ;, or ] are ignored)
; This is also a comment
] And this too

https://www.youtube.com/watch?v=VIDEO_ID_1
https://www.youtube.com/watch?v=VIDEO_ID_2
https://www.youtube.com/playlist?list=PLAYLIST_ID
https://vimeo.com/123456789
```

One URL per line. Empty lines and comments (prefixed with `#`, `;`, or `]`) are skipped.

## Configuration Files

Store default options in a config file so you don't repeat them every time.

### Config File Locations (checked in order)

1. **Portable config:** `yt-dlp.conf` in the same directory as the yt-dlp binary
2. **User config (XDG):** `~/.config/yt-dlp/config` (Linux/macOS)
3. **User config (AppData):** `%APPDATA%\yt-dlp\config.txt` (Windows)
4. **System config:** `/etc/yt-dlp.conf` (Linux)

### Custom Config Location

```bash
# Use a specific config file
yt-dlp --config-locations "/path/to/my-config.txt"

# Use multiple config files
yt-dlp --config-locations "base.conf" --config-locations "extra.conf"

# Read config from stdin
echo "--format best" | yt-dlp --config-locations -

# Ignore all config files
yt-dlp --ignore-config "URL"
```

### Config File Format

```
# ~/.config/yt-dlp/config

# Best quality, merged
-f bestvideo+bestaudio
--merge-output-format mkv

# Embed everything
--embed-metadata
--embed-thumbnail
--embed-subs
--embed-chapters

# Subtitles
--write-subs
--sub-langs en

# Output template
-o %(channel)s/%(upload_date>%Y-%m-%d)s - %(title).200B [%(id)s].%(ext)s

# Archive tracking
--download-archive ~/.config/yt-dlp/archive.txt

# Network
-N 4
--throttled-rate 100K

# Avoid re-downloads
--no-overwrites
```

Each line is one option. Options that take values can use `option value` or `option=value`. Comments start with `#`.

## Download Archive

The `--download-archive` flag is the core mechanism for incremental downloads. It tracks which videos have been downloaded and skips them on future runs.

```bash
# First run: downloads everything, records IDs
yt-dlp --download-archive archive.txt "PLAYLIST_URL"

# Second run: only downloads new videos
yt-dlp --download-archive archive.txt "PLAYLIST_URL"
```

### Archive File Contents

Plain text, one entry per line:

```
youtube dQw4w9WgXcQ
youtube xvFZjo5PgG0
vimeo 123456789
```

Format: `extractor_key video_id`

### Archive Management

```bash
# Mark videos as downloaded without actually downloading
yt-dlp --simulate --force-write-archive --download-archive archive.txt "PLAYLIST_URL"

# Stop downloading when hitting an already-archived video
yt-dlp --download-archive archive.txt --break-on-existing "PLAYLIST_URL"

# Reset break-on-existing per URL when using batch files
yt-dlp --download-archive archive.txt --break-on-existing --break-per-input \
  -a urls.txt
```

## Incremental Download Patterns

### Resilient Playlist Archiver

```bash
# Handles interruptions gracefully
yt-dlp \
  --ignore-errors \
  --continue \
  --no-overwrites \
  --download-archive archive.txt \
  -f "bestvideo+bestaudio" \
  --merge-output-format mkv \
  -o "%(channel)s/%(upload_date>%Y-%m-%d)s - %(title).200B [%(id)s].%(ext)s" \
  "PLAYLIST_URL"
```

### Nightly Channel Sync

```bash
# Run via cron/scheduled task -- downloads only new videos
yt-dlp \
  --download-archive ~/archives/channel.txt \
  --break-on-existing \
  -f "bestvideo+bestaudio" \
  --merge-output-format mkv \
  --embed-metadata --embed-thumbnail \
  -o "~/Videos/%(channel)s/%(upload_date>%Y-%m-%d)s - %(title).200B [%(id)s].%(ext)s" \
  "https://www.youtube.com/@ChannelName"
```

### Multi-Channel Batch Sync

Create `channels.txt`:
```
https://www.youtube.com/@Channel1
https://www.youtube.com/@Channel2
https://www.youtube.com/@Channel3
```

```bash
yt-dlp \
  --download-archive ~/archives/master.txt \
  --break-on-existing \
  --break-per-input \
  -f "bestvideo+bestaudio" \
  --merge-output-format mkv \
  --embed-metadata \
  -o "~/Videos/%(channel)s/%(upload_date>%Y-%m-%d)s - %(title).200B.%(ext)s" \
  -a channels.txt
```

### Audio Podcast Archiver

```bash
yt-dlp \
  --download-archive ~/archives/podcasts.txt \
  --break-on-existing \
  -x --audio-format mp3 --audio-quality 0 \
  --embed-metadata --embed-thumbnail \
  -o "~/Podcasts/%(channel)s/%(upload_date>%Y-%m-%d)s - %(title).200B.%(ext)s" \
  -a podcast-feeds.txt
```

## Controlling Download Behavior

```bash
# Don't overwrite existing files
yt-dlp --no-overwrites "URL"

# Continue partially downloaded files
yt-dlp --continue "URL"

# Abort after downloading 10 videos
yt-dlp --max-downloads 10 "PLAYLIST_URL"

# Skip remaining playlist after 3 consecutive errors
yt-dlp --skip-playlist-after-errors 3 "PLAYLIST_URL"
```

## Common Flags Reference

| Flag | Effect |
|------|--------|
| `-a FILE` / `--batch-file` | Read URLs from file |
| `--config-locations PATH` | Use custom config file |
| `--ignore-config` | Skip all config files |
| `--download-archive FILE` | Track downloaded videos, skip duplicates |
| `--break-on-existing` | Stop on first already-archived video |
| `--break-per-input` | Reset break flags per URL in batch |
| `--force-write-archive` | Write archive even with `--simulate` |
| `--no-overwrites` | Don't overwrite existing files |
| `--continue` / `-c` | Resume partially downloaded files |
| `--max-downloads N` | Stop after N downloads |
| `--ignore-errors` | Continue past download errors |
| `--skip-playlist-after-errors N` | Skip playlist after N errors |

## Gotchas and Edge Cases

- **Config files expand `~` but not shell variables.** `~/Videos` works (yt-dlp expands `~`), but `$HOME` and `%USERPROFILE%` are NOT expanded. Use `~` or absolute paths.
- **`--break-on-existing` assumes chronological order.** If new videos are inserted in the middle of a playlist, they'll be missed. Use without `--break-on-existing` for reordered playlists.
- **`--break-per-input` is essential for batch files with `--break-on-existing`.** Without it, hitting an existing video in the first URL stops processing all remaining URLs.
- **Archive files grow forever.** For long-running archives, the file can get large. This doesn't affect performance much (it's a linear scan), but you may want to periodically clean it.
- **Comments in batch files use `#`, `;`, or `]`.** The `]` prefix is unusual but supported. Lines starting with these characters are always skipped.
- **Windows batch files need double `%`.** In `.bat` scripts, `%(title)s` must be `%%(title)s`. This doesn't apply to yt-dlp config files, only Windows batch scripts.
- **`--ignore-errors` is important for large batch jobs.** Without it, a single failed video stops the entire batch. With it, errors are logged and skipped.
- **Config file options are prepended to CLI options.** If a config file sets `-f best` and you run `yt-dlp -f worst`, the CLI option wins (last one wins).
- **Multiple config files stack.** System, user, and portable configs are all loaded. Use `--ignore-config` to start clean, then `--config-locations` for a specific file.

## Sources

- [yt-dlp GitHub README](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp man page (Arch)](https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en)
- [yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
- [Configuration Files - yt-dlp Mintlify](https://mintlify.wiki/yt-dlp/yt-dlp/core-concepts/configuration)
- [yt-dlp cheat sheet - Ditig](https://www.ditig.com/yt-dlp-cheat-sheet)
- [BHL Archival Curation - yt-dlp Config](https://sites.google.com/a/umich.edu/bhl-archival-curation/digital-curation/download-videos-from-youtube/yt-dlp-config-file-setup)
- [yt-dlp ArchWiki](https://wiki.archlinux.org/title/Yt-dlp)
