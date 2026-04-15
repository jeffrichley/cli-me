# Playlist and Channel Handling

Download playlists and channels with fine-grained control over which items to download, date filtering, and archive tracking to avoid re-downloads.

## Playlist Indexing

The `-I` / `--playlist-items` flag selects specific items using ranges, indices, and step values.

```bash
# Download items 1 through 5
yt-dlp -I 1:5 "PLAYLIST_URL"

# Download specific items by index
yt-dlp -I 1,3,5,7 "PLAYLIST_URL"

# Download last 5 items
yt-dlp -I -5: "PLAYLIST_URL"

# Download every other item (step of 2)
yt-dlp -I 1::2 "PLAYLIST_URL"

# Download items 1-3 and 7-10
yt-dlp -I "1:3,7:10" "PLAYLIST_URL"

# Download from item 10 to the end
yt-dlp -I 10: "PLAYLIST_URL"

# Download only the first item
yt-dlp -I 1 "PLAYLIST_URL"

# Reverse order (step of -1)
yt-dlp -I ::-1 "PLAYLIST_URL"
```

Index syntax: `START:STOP[:STEP]` -- similar to Python slicing. Negative indices count from the end.

## Date Filtering

```bash
# Download only videos uploaded after a date
yt-dlp --dateafter 20240101 "PLAYLIST_URL"

# Download only videos uploaded before a date
yt-dlp --datebefore 20241231 "PLAYLIST_URL"

# Download videos within a date range
yt-dlp --dateafter 20240101 --datebefore 20240630 "PLAYLIST_URL"

# Download videos from a specific date
yt-dlp --date 20240315 "PLAYLIST_URL"
```

Date format is `YYYYMMDD`. Also accepts relative dates like `now-1week`, `today-1month`, `now-30day`.

```bash
# Videos from the last 7 days
yt-dlp --dateafter now-7day "PLAYLIST_URL"

# Videos from the last month
yt-dlp --dateafter now-1month "PLAYLIST_URL"
```

## Match Filters

```bash
# Only download videos longer than 5 minutes
yt-dlp --match-filter "duration > 300" "PLAYLIST_URL"

# Only download videos shorter than 10 minutes
yt-dlp --match-filter "duration < 600" "PLAYLIST_URL"

# Only download videos with more than 1000 views
yt-dlp --match-filter "view_count > 1000" "PLAYLIST_URL"

# Skip live streams
yt-dlp --match-filter "!is_live" "PLAYLIST_URL"

# Skip age-restricted content
yt-dlp --match-filter "age_limit < 18" "PLAYLIST_URL"

# Title contains a keyword
yt-dlp --match-filter "title ~= 'tutorial'" "PLAYLIST_URL"
```

## Archive Files

The `--download-archive` flag writes video IDs to a file after download and skips any ID already in that file. This is the primary mechanism for incremental downloads.

```bash
# Download playlist, recording what's been downloaded
yt-dlp --download-archive archive.txt "PLAYLIST_URL"

# Run the same command later -- already-downloaded videos are skipped
yt-dlp --download-archive archive.txt "PLAYLIST_URL"

# Combine with channel URL for ongoing channel archiving
yt-dlp --download-archive archive.txt "https://www.youtube.com/@ChannelName"
```

### Archive File Format

The archive file is plain text, one entry per line:

```
youtube VIDEO_ID_1
youtube VIDEO_ID_2
vimeo VIDEO_ID_3
```

Format: `extractor_key VIDEO_ID`

### Simulating Archive Updates

```bash
# Add videos to archive without downloading (mark as "already downloaded")
yt-dlp --simulate --force-write-archive --download-archive archive.txt "PLAYLIST_URL"
```

### Breaking on Existing

```bash
# Stop when hitting an already-archived video (efficient for large playlists)
yt-dlp --download-archive archive.txt --break-on-existing "PLAYLIST_URL"

# Reset break behavior per URL in batch mode
yt-dlp --download-archive archive.txt --break-on-existing --break-per-input \
  -a urls.txt
```

## Channel Downloads

```bash
# Download all videos from a channel
yt-dlp "https://www.youtube.com/@ChannelName"

# Download channel with organized folder structure
yt-dlp -o "%(channel)s/%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s" \
  "https://www.youtube.com/@ChannelName"

# Incremental channel archiving with best quality
yt-dlp --download-archive channel-archive.txt \
  -f "bestvideo+bestaudio" --merge-output-format mkv \
  -o "%(channel)s/%(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s" \
  "https://www.youtube.com/@ChannelName"

# Channel tabs (videos, shorts, live, etc.)
yt-dlp "https://www.youtube.com/@ChannelName/videos"
yt-dlp "https://www.youtube.com/@ChannelName/shorts"
yt-dlp "https://www.youtube.com/@ChannelName/streams"
```

## Limiting Downloads

```bash
# Download at most 10 videos
yt-dlp --max-downloads 10 "PLAYLIST_URL"

# Skip playlist after 3 consecutive errors
yt-dlp --skip-playlist-after-errors 3 "PLAYLIST_URL"
```

## Playlist vs Single Video

```bash
# URL references both video and playlist -- download only the video
yt-dlp --no-playlist "https://www.youtube.com/watch?v=ID&list=PLAYLIST_ID"

# URL references both -- download the full playlist
yt-dlp --yes-playlist "https://www.youtube.com/watch?v=ID&list=PLAYLIST_ID"
```

## Resilient Playlist Download

```bash
# Continue on errors, don't overwrite, track archive
yt-dlp --ignore-errors --continue --no-overwrites \
  --download-archive archive.txt \
  "PLAYLIST_URL"
```

## Gotchas and Edge Cases

- **`--break-on-existing` assumes playlist order is chronological.** If a playlist is reordered, breaking on the first existing video might skip new ones added in the middle.
- **Archive files are append-only.** yt-dlp never removes entries. If you delete a downloaded file, you must manually remove its line from the archive to re-download it.
- **Channel URLs may download thousands of videos.** Always use `--download-archive` for channels to support interrupted/resumable downloads.
- **`--dateafter` and `--datebefore` use the upload date, not the publish date.** For some sites, these may differ.
- **Relative dates don't use spaces.** It's `now-7day` not `now - 7 day`.
- **`-I` uses 1-based indexing.** The first video is index 1, not 0.
- **YouTube Shorts and livestreams are separate tabs.** `@ChannelName` may not include all content types. Specify `/videos`, `/shorts`, or `/streams` explicitly.
- **`--match-filter` fields must exist.** If a video doesn't have `view_count` metadata, the filter may skip it or error. Use the `?` operator for optional fields.
- **Large playlists may hit rate limits.** YouTube may throttle metadata extraction for playlists with hundreds of videos. Use `--sleep-requests 1` to add delays.

## Sources

- [yt-dlp GitHub README](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp man page (Arch)](https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en)
- [yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
- [yt-dlp cheat sheet - Ditig](https://www.ditig.com/yt-dlp-cheat-sheet)
- [RapidSeedbox yt-dlp Guide](https://www.rapidseedbox.com/blog/yt-dlp-complete-guide)
