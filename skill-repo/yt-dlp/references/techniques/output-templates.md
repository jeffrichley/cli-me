# Output Templates

The `-o` / `--output` flag controls filenames and directory structure. Templates use Python string formatting with `%(field)s` placeholders.

## Basic Syntax

```bash
# Default template
yt-dlp -o "%(title)s [%(id)s].%(ext)s" "URL"

# Simple title + extension
yt-dlp -o "%(title)s.%(ext)s" "URL"

# Set download directory with -P, filename with -o
yt-dlp -P "~/Downloads" -o "%(title)s.%(ext)s" "URL"
```

## Common Template Variables

### Video Metadata
| Variable | Description | Example |
|----------|-------------|---------|
| `%(id)s` | Video ID | `dQw4w9WgXcQ` |
| `%(title)s` | Video title | `Never Gonna Give You Up` |
| `%(fulltitle)s` | Full title (no truncation) | Same, but guaranteed untruncated |
| `%(ext)s` | File extension | `mp4` |
| `%(alt_title)s` | Secondary title | |
| `%(description)s` | Full description | |
| `%(display_id)s` | Alternative ID | |

### Uploader / Channel
| Variable | Description |
|----------|-------------|
| `%(uploader)s` | Uploader name |
| `%(uploader_id)s` | Uploader ID |
| `%(channel)s` | Channel name |
| `%(channel_id)s` | Channel ID |
| `%(channel_url)s` | Channel URL |

### Dates and Times
| Variable | Description | Format |
|----------|-------------|--------|
| `%(upload_date)s` | Upload date | `YYYYMMDD` |
| `%(release_date)s` | Release date | `YYYYMMDD` |
| `%(release_year)s` | Release year | `YYYY` |
| `%(timestamp)s` | Unix timestamp | |
| `%(modified_date)s` | Modified date | `YYYYMMDD` |

### Counts and Stats
| Variable | Description |
|----------|-------------|
| `%(view_count)s` | View count |
| `%(like_count)s` | Like count |
| `%(dislike_count)s` | Dislike count |
| `%(comment_count)s` | Comment count |
| `%(channel_follower_count)s` | Subscriber count |

### Video Properties
| Variable | Description |
|----------|-------------|
| `%(duration)s` | Duration in seconds |
| `%(duration_string)s` | Duration as `HH:MM:SS` |
| `%(age_limit)s` | Age restriction |
| `%(is_live)s` | Whether it's a live stream |
| `%(was_live)s` | Whether it was a live stream |
| `%(availability)s` | Availability status |

### Playlist Context
| Variable | Description |
|----------|-------------|
| `%(playlist)s` | Playlist name (or ID) |
| `%(playlist_title)s` | Playlist title |
| `%(playlist_id)s` | Playlist ID |
| `%(playlist_index)s` | 1-based position in playlist |
| `%(playlist_autonumber)s` | Auto-numbered position (zero-padded) |
| `%(playlist_count)s` | Total playlist items |
| `%(n_entries)s` | Total entries |
| `%(playlist_uploader)s` | Playlist creator |

### Series / Episode / Chapter
| Variable | Description |
|----------|-------------|
| `%(series)s` | Series name |
| `%(season)s` | Season name |
| `%(season_number)s` | Season number |
| `%(episode)s` | Episode name |
| `%(episode_number)s` | Episode number |
| `%(chapter)s` | Chapter name |
| `%(chapter_number)s` | Chapter number |
| `%(section_title)s` | Section title (download-sections) |

### Music / Track
| Variable | Description |
|----------|-------------|
| `%(track)s` | Track name |
| `%(track_number)s` | Track number |
| `%(artist)s` | Artist |
| `%(artists)s` | Artists (list) |
| `%(album)s` | Album |
| `%(album_artist)s` | Album artist |
| `%(genre)s` | Genre |
| `%(disc_number)s` | Disc number |

### Source / Extractor
| Variable | Description |
|----------|-------------|
| `%(extractor)s` | Extractor name |
| `%(extractor_key)s` | Extractor key |
| `%(webpage_url)s` | Original URL |
| `%(webpage_url_domain)s` | Domain name |
| `%(epoch)s` | Download timestamp |
| `%(autonumber)s` | Auto-incrementing number |

## Formatting Options

```bash
# Truncate title to 200 bytes (UTF-8 safe)
yt-dlp -o "%(title).200B.%(ext)s" "URL"

# Truncate uploader to 30 bytes
yt-dlp -o "%(uploader).30B - %(title).200B.%(ext)s" "URL"

# Zero-pad playlist index to 3 digits
yt-dlp -o "%(playlist_index)03d - %(title)s.%(ext)s" "URL"

# Format date with strftime (use > separator)
yt-dlp -o "%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s" "URL"

# Use autonumber with 5-digit padding
yt-dlp -o "%(autonumber)05d - %(title)s.%(ext)s" "URL"
```

## Organizing Downloads into Folders

```bash
# By uploader/channel
yt-dlp -o "%(uploader)s/%(title)s.%(ext)s" "URL"

# By uploader and upload date
yt-dlp -o "%(uploader)s/%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s" "URL"

# Playlist folder structure
yt-dlp -o "%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s" "PLAYLIST_URL"

# By website domain
yt-dlp -o "%(webpage_url_domain)s/%(uploader)s/%(title)s.%(ext)s" "URL"

# Set base path with -P and relative structure with -o
yt-dlp -P "~/Videos" -o "%(uploader)s/%(title)s.%(ext)s" "URL"
```

## Per-Type Output Templates

Different file types can have different templates using the `TYPE:` prefix.

```bash
# Different template for subtitles vs video
yt-dlp \
  -o "%(title)s.%(ext)s" \
  -o "subtitle:%(title)s.%(sub_lang)s.%(ext)s" \
  --write-subs "URL"

# Different path for thumbnails
yt-dlp \
  -o "%(title)s.%(ext)s" \
  -o "thumbnail:thumbnails/%(title)s.%(ext)s" \
  --write-thumbnail "URL"

# Chapter split output template
yt-dlp \
  -o "chapter:%(title)s - %(chapter)s.%(ext)s" \
  --split-chapters "URL"
```

Supported type prefixes: `subtitle`, `thumbnail`, `description`, `infojson`, `link`, `pl_thumbnail`, `pl_description`, `pl_infojson`, `chapter`, `pl_video`.

## Per-Type Paths (-P)

```bash
# Put temp files in a temp directory
yt-dlp -P "~/Videos" -P "temp:~/tmp" "URL"

# Put thumbnails in a subfolder
yt-dlp -P "~/Videos" -P "thumbnail:~/Videos/thumbs" --write-thumbnail "URL"
```

## Handling Missing Values

```bash
# Change the placeholder for missing fields (default is "NA")
yt-dlp --output-na-placeholder "Unknown" -o "%(artist)s - %(title)s.%(ext)s" "URL"

# Restrict filenames to ASCII (replace special chars with underscores)
yt-dlp --restrict-filenames -o "%(title)s.%(ext)s" "URL"

# Restrict to Windows-safe characters (removes <>:"/\|?*)
yt-dlp --windows-filenames -o "%(title)s.%(ext)s" "URL"
```

## Gotchas and Edge Cases

- **Windows batch files need double percent signs.** In `.bat` files, `%(title)s` must be written as `%%(title)s`. Environment variables like `%HOMEPATH%` stay as-is.
- **Filename length limits exist.** Most filesystems limit filenames to 255 bytes. Use `.200B` truncation to stay safe: `-o "%(title).200B.%(ext)s"`.
- **`%(playlist)s` may be empty for single videos.** When downloading a single video (not part of a playlist), playlist-related variables will be empty or "NA".
- **`%(ext)s` is set by yt-dlp, not by you.** Don't hardcode extensions like `.mp4`. Use `%(ext)s` so it matches the actual downloaded format.
- **`--restrict-filenames` replaces spaces and special characters.** It converts `&`, spaces, and unicode to ASCII-safe characters with underscores.
- **Date formatting uses `>` separator.** To format a date: `%(upload_date>%Y-%m-%d)s`. The `>` separates the field name from the strftime format.
- **Path separators create directories.** Using `/` in the template (e.g., `%(uploader)s/%(title)s`) automatically creates subdirectories.

## Sources

- [yt-dlp GitHub README](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp man page (Arch)](https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en)
- [How to set a custom output filename in yt-dlp - Ditig](https://www.ditig.com/set-yt-dlp-output-filename)
- [yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
- [Arch Wiki - yt-dlp](https://wiki.archlinux.org/title/Yt-dlp)
