---
name: yt-dlp
description: Video/audio download CLI for yt-dlp. Use when asked to download video,
  download audio, extract audio from URL, download playlist, download channel,
  get subtitles, get thumbnails, download from YouTube, download from TikTok,
  download from Twitter, download from Instagram, download Instagram reel,
  download from Vimeo, download Twitch clip, rip audio, save video, archive channel, batch download,
  download music, remove sponsor segments, SponsorBlock, list formats, get video info, download
  with cookies, remux downloaded video, embed subtitles, embed metadata, or
  any media downloading from websites.
---

# yt-dlp — cli-me skill

Intent-based CLI for yt-dlp. This skill wraps the real yt-dlp binary —
it does not download media in Python.

## Prerequisites

- yt-dlp must be installed and in PATH
  - Windows: `pip install yt-dlp` or `winget install yt-dlp`
  - macOS: `brew install yt-dlp`
  - Linux: `pip install yt-dlp` or see https://github.com/yt-dlp/yt-dlp#installation
- ffmpeg (required for audio extraction, merging formats, post-processing)
  - Windows: `winget install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `apt install ffmpeg`
- Python 3.12+
- uv (Python package runner): https://docs.astral.sh/uv/getting-started/installation/

## CLI Commands

Run commands from the skill's `scripts/` directory:
```bash
cd <skill-dir>/scripts
uv run yt_dlp_cli.py <group> <command> [options]
```

Or from any directory using the full path:
```bash
uv run --project <skill-dir>/scripts <skill-dir>/scripts/yt_dlp_cli.py <group> <command> [options]
```

To discover available flags for any command:
```bash
uv run yt_dlp_cli.py <group> <command> --help
```

### Command Groups

| Group | Purpose |
|-------|---------|
| `download` | Download video/audio from URLs with format selection |
| `info` | Query formats, metadata, subtitles, thumbnails without downloading |
| `config` | Manage cookies and download archives |
| `process` | Post-process: SponsorBlock, chapters, remux, embed metadata |
| `batch` | Batch downloads from file, incremental sync, search |

### Quick Examples

```bash
# Download a video (best quality)
uv run yt_dlp_cli.py download video "https://youtube.com/watch?v=..."

# Download audio only as MP3
uv run yt_dlp_cli.py download audio "https://youtube.com/watch?v=..." --format mp3

# Download playlist
uv run yt_dlp_cli.py download playlist "https://youtube.com/playlist?list=..."

# List available formats
uv run yt_dlp_cli.py info formats "https://youtube.com/watch?v=..."

# Get video metadata as JSON
uv run yt_dlp_cli.py info metadata "https://youtube.com/watch?v=..."

# Search for videos without downloading (JSON output by default)
uv run yt_dlp_cli.py info search "lo-fi beats" --max-results 10
uv run yt_dlp_cli.py info search "lo-fi beats" --pretty
uv run yt_dlp_cli.py info search "lo-fi beats" --provider youtube-music

# Download with SponsorBlock removal
uv run yt_dlp_cli.py process sponsorblock "https://youtube.com/watch?v=..." --remove sponsor,selfpromo

# Batch download from file
uv run yt_dlp_cli.py batch from-file urls.txt --archive downloaded.txt

# Batch search and download
uv run yt_dlp_cli.py batch search "lofi hip hop" --max-results 5 --provider youtube-music --format mp3

# Download with browser cookies
uv run yt_dlp_cli.py config cookies --browser chrome
uv run yt_dlp_cli.py download video "https://..." --cookies cookies.txt
```

### Search Providers

The `info search` and `batch search` commands accept a `--provider` flag to select the search backend:

| Provider | Description |
|----------|-------------|
| `youtube` | YouTube (default) — general video search |
| `youtube-music` | YouTube Music — music-focused results |
| `youtube-videos` | YouTube Videos — filters to video content only |
| `soundcloud` | SoundCloud — music and audio tracks |

`info search` outputs JSON by default (machine-readable). Use `--pretty` for human-readable output.

### Common Task Mapping

| Task | Command | Notes |
|------|---------|-------|
| Download YouTube video | `download video URL` | Best video+audio by default |
| Rip audio from video | `download audio URL --format mp3` | Uses ffmpeg for conversion |
| Download 720p max | `download video URL --max-height 720` | Format selection filter |
| Download entire channel | `download channel URL --archive archive.txt` | Incremental with archive |
| Get subtitles only | `info subtitles URL --download --langs en` | Downloads subtitle files |
| Remove sponsors | `process sponsorblock URL --remove sponsor` | Requires SponsorBlock API |
| Archive playlist | `batch sync URL --archive archive.txt` | Skip already-downloaded |
| Search without downloading | `info search QUERY --pretty` | JSON by default, `--pretty` for readable |
| Search by music provider | `info search QUERY --provider youtube-music` | See Search Providers table |
| Search and download | `batch search QUERY --provider soundcloud` | Downloads all results |

### Default Behavior

- **Force overwrites:** All commands include `--force-overwrites` by default to
  avoid interactive prompts in agent context. The `download` and `process`
  commands support `--no-overwrites` to override this.
- **Files download to the current working directory** unless `--output-dir` is specified.

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how a command works under the hood, check the
relevant technique page — it explains the yt-dlp flags, common mistakes,
and parameter recommendations.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

**Important:** Always read an existing page before modifying it. Do not create
new pages that duplicate existing topics — update the existing page instead.

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Append a timestamped entry to `references/log.md` with what you did and
   what you learned
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
