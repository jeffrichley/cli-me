# yt-dlp QA Playbook

## Command Groups and Expected Behavior

### 1. download

#### `download video <url>`
- **Input**: URL (YouTube, Vimeo, etc.), optional format/quality flags
- **Expected**: Downloads video+audio to output path
- **Verify**: File exists, has video+audio streams, resolution matches request
- **Edge cases**: Age-restricted, geo-blocked, private video, live stream URL

#### `download audio <url>`
- **Input**: URL, optional --format (mp3, opus, flac, wav, m4a)
- **Expected**: Downloads and extracts audio to specified format
- **Verify**: Audio file exists, correct codec, no video stream, duration matches
- **Edge cases**: Video with no audio, audio-only source, very short clip

#### `download playlist <url>`
- **Input**: Playlist URL, optional --items range, --output template
- **Expected**: Downloads all (or specified) videos from playlist
- **Verify**: Correct number of files, archive file updated, output template applied
- **Edge cases**: Empty playlist, private items, very large playlist

#### `download channel <url>`
- **Input**: Channel URL, optional --archive, --tabs
- **Expected**: Downloads channel videos with archive tracking
- **Verify**: Files downloaded, archive file populated correctly
- **Edge cases**: Channel with no videos, channel tabs (shorts, streams)

### 2. info

#### `info formats <url>`
- **Input**: URL
- **Expected**: Prints available formats table (JSON by default)
- **Verify**: Output contains format_id, ext, resolution, codec info
- **Edge cases**: URL with no formats, audio-only content

#### `info metadata <url>`
- **Input**: URL
- **Expected**: Prints metadata JSON (title, uploader, duration, etc.)
- **Verify**: JSON is valid, contains required fields
- **Edge cases**: Video with minimal metadata, private video

#### `info subtitles <url>`
- **Input**: URL, optional --download, --langs
- **Expected**: Lists available subtitles or downloads them
- **Verify**: Subtitle languages listed, files downloaded if requested
- **Edge cases**: No subtitles available, auto-generated only

#### `info thumbnails <url>`
- **Input**: URL, optional --download
- **Expected**: Lists available thumbnails or downloads them
- **Verify**: Thumbnail URLs listed, files downloaded if requested

### 3. config

#### `config cookies --browser <browser>`
- **Input**: Browser name (chrome, firefox, etc.)
- **Expected**: Extracts cookies to cookies.txt
- **Verify**: Cookie file exists, is Netscape format
- **Edge cases**: Browser not installed, browser running (locked DB)

#### `config archive --check <file> <url>`
- **Input**: Archive file path, URL to check
- **Expected**: Reports whether URL is in archive
- **Verify**: Correct yes/no response

### 4. process

#### `process sponsorblock <url> --remove <categories>`
- **Input**: URL, categories to remove (sponsor, selfpromo, etc.)
- **Expected**: Downloads and removes sponsor segments
- **Verify**: Output file exists, duration is shorter than original
- **Edge cases**: Video with no sponsor segments, all categories

#### `process chapters <url> --split`
- **Input**: URL with chapters
- **Expected**: Downloads and splits into chapter files
- **Verify**: Multiple output files, one per chapter, correct durations

#### `process remux <url> --format <container>`
- **Input**: URL, target container (mp4, mkv, webm)
- **Expected**: Downloads and remuxes to specified container
- **Verify**: Output has correct container format, streams preserved

#### `process embed <url> --subs --thumbnail --metadata --chapters`
- **Input**: URL, embedding flags
- **Expected**: Downloads with embedded metadata/subs/thumbnail/chapters
- **Verify**: Embedded streams present in output file

### 5. batch

#### `batch from-file <file>`
- **Input**: Text file with one URL per line, optional --archive
- **Expected**: Downloads all URLs, skips archived
- **Verify**: All files downloaded, archive updated

#### `batch sync <url> --archive <file>`
- **Input**: Playlist/channel URL, archive file
- **Expected**: Downloads only new videos since last sync
- **Verify**: New videos downloaded, existing skipped

#### `batch search <query>`
- **Input**: Search query string, optional --max-results
- **Expected**: Searches and downloads matching videos
- **Verify**: Search results match query, correct number of results

## Test Tiers

### Tier 1: Command Graph (mocked subprocess)
- Verify correct yt-dlp argument construction
- No binary needed
- `@pytest.mark.command_graph`

### Tier 2: Integration (real yt-dlp)
- Real downloads against known stable URLs
- Deep assertions: file exists, correct codec, duration, streams
- `@pytest.mark.integration`
- Skip if yt-dlp not installed

### Tier 3: Manual (human review)
- Visual quality of downloaded videos
- Audio quality of extracted audio
- Subtitle readability
- `@pytest.mark.manual`

## Test URLs

Use these known-stable, short public domain videos for testing:
- YouTube: `https://www.youtube.com/watch?v=BaW_jenozKc` (Creative Commons, short)
- YouTube playlist: (find a small public domain playlist)
- Note: Tests should timeout after 60s to prevent hanging on slow downloads
