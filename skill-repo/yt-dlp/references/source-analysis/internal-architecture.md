# yt-dlp Internal Architecture Analysis

Source: yt-dlp v2026.03.17

## Project Structure

```
yt_dlp/
    __init__.py          # CLI entry point: main(), _real_main(), parse_options()
    YoutubeDL.py         # Core class (~4500 lines) — orchestrates everything
    options.py           # CLI option parser (optparse-based, ~2000 lines)
    version.py           # Version string and release metadata
    cache.py             # Filesystem cache for client IDs, signatures
    plugins.py           # Plugin loading system (namespace packages)
    globals.py           # Global state containers (Indirect pattern)
    cookies.py           # Browser cookie extraction
    extractor/
        __init__.py      # Extractor registry and plugin spec
        common.py        # InfoExtractor base class
        extractors/      # ~1800+ site-specific extractors
        generic.py       # Fallback generic extractor
    postprocessor/
        __init__.py      # PP registry and plugin spec
        common.py        # PostProcessor base class
        ffmpeg.py        # FFmpeg-based PPs (largest: audio extract, merge, convert, metadata, etc.)
        embedthumbnail.py
        exec.py
        metadataparser.py
        modify_chapters.py
        movefilesafterdownload.py
        sponsorblock.py
        xattrpp.py
    downloader/
        common.py        # Base downloader
        external.py      # External downloader wrappers (aria2c, curl, wget, etc.)
        hls.py           # HLS/m3u8 downloader
        http.py          # HTTP downloader
        rtmp.py          # RTMP downloader
    networking/
        common.py        # Request handler base
        impersonate.py   # Browser impersonation
        exceptions.py    # Network error hierarchy
    utils/
        __init__.py      # Re-exports from submodules
        _utils.py        # Core utilities (~6000 lines)
        _jsruntime.py    # JavaScript runtime integration (Deno, Node, Bun, QuickJS)
        _legacy.py       # Deprecated utilities
        _deprecated.py   # Deprecated names
        networking.py    # HTTP header/proxy utilities
        progress.py      # Progress bar rendering
        traversal.py     # traverse_obj deep getter
        jslib/           # Bundled JS libraries
    compat/              # Python version compatibility
    update.py            # Self-update system
```

## Data Flow

```
URL → main() → parseOpts() → YoutubeDL(params)
  → extract_info(url)
    → find matching InfoExtractor via ie.suitable(url)
    → ie._real_extract(url) → info_dict
  → process_ie_result(info_dict)
    → if playlist: iterate entries, recurse
    → if video: build_format_selector() → select formats
  → process_info(info_dict)
    → pre_process (PP when='pre_process')
    → download file(s) via Downloader
    → post_process (PP when='post_process')
    → after_move (PP when='after_move')
```

## Extractor System

### Base Class (`extractor/common.py:107`)

```python
class InfoExtractor:
    IE_NAME = ...       # Human-readable name
    IE_DESC = ...       # Description (False to hide)
    _VALID_URL = ...    # Regex to match URLs
    _WORKING = True     # Whether extractor works

    def suitable(cls, url) -> bool     # Class method, checks _VALID_URL
    def _real_extract(self, url) -> dict  # Override this — returns info_dict
```

### Extractor Registration
- `extractor/__init__.py:9-14` registers via `PluginSpec(module_name='extractor', suffix='IE', ...)`
- All classes ending in `IE` are auto-discovered
- Plugin extractors from `yt_dlp_plugins.extractor` take priority over built-in ones
- `gen_extractor_classes()` returns all extractors in priority order
- `get_info_extractor(ie_name)` returns class by name (appends `IE`)

### Info Dict Fields (returned by extractors)
Key fields from `_format_fields` (YoutubeDL.py:605-614):
- **Identity**: `id`, `title`, `display_id`, `ext`, `webpage_url`
- **Metadata**: `description`, `uploader`, `channel`, `upload_date`, `duration`, `view_count`, `like_count`
- **Series**: `series`, `season_number`, `episode_number`
- **Music**: `track`, `artist`, `album`, `genre`
- **Formats**: list of format dicts with `url`, `ext`, `format_id`, `height`, `width`, `vcodec`, `acodec`, `tbr`, etc.
- **Subtitles**: dict of `{lang: [{url, ext}]}`
- **Thumbnails**: list of `{url, height, width, id}`
- **Playlist**: `_type='playlist'`, `entries` (list/generator of info_dicts)

### Numeric Fields (YoutubeDL.py:594-603)
```python
_NUMERIC_FIELDS = {
    'width', 'height', 'asr', 'audio_channels', 'fps',
    'tbr', 'abr', 'vbr', 'filesize', 'filesize_approx',
    'timestamp', 'release_timestamp', 'available_at',
    'duration', 'view_count', 'like_count', 'dislike_count', 'repost_count', 'save_count',
    'average_rating', 'comment_count', 'age_limit',
    'start_time', 'end_time',
    'chapter_number', 'season_number', 'episode_number',
    'track_number', 'disc_number', 'release_year',
}
```

## Postprocessor System

### Base Class (`postprocessor/common.py:36`)

```python
class PostProcessor(metaclass=PostProcessorMetaClass):
    def run(self, info) -> (list_of_files_to_delete, info_dict):
        ...
```

The `PostProcessorMetaClass` wraps `run()` to auto-fire progress hooks with `started`/`finished` status.

### POSTPROCESS_WHEN Stages (`utils/_utils.py:2852`)
```python
POSTPROCESS_WHEN = (
    'pre_process',      # Before any download
    'after_filter',     # After match_filter check
    'video',            # After video info resolved
    'before_dl',        # Just before download
    'post_process',     # After download (default)
    'after_move',       # After files moved to final location
    'after_video',      # After all processing for one video
    'playlist',         # After entire playlist
)
```

### Built-in Postprocessors (`postprocessor/__init__.py`)

| Class | Key | Function |
|-------|-----|----------|
| `FFmpegExtractAudioPP` | `FFmpegExtractAudio` | Convert to audio-only |
| `FFmpegVideoConvertorPP` | `FFmpegVideoConvertor` | Re-encode video |
| `FFmpegVideoRemuxerPP` | `FFmpegVideoRemuxer` | Remux container |
| `FFmpegMergerPP` | `FFmpegMerger` | Merge video+audio streams |
| `FFmpegMetadataPP` | `FFmpegMetadata` | Embed metadata tags |
| `FFmpegEmbedSubtitlePP` | `FFmpegEmbedSubtitle` | Embed subtitles |
| `FFmpegSubtitlesConvertorPP` | `FFmpegSubtitlesConvertor` | Convert subtitle format |
| `FFmpegThumbnailsConvertorPP` | `FFmpegThumbnailsConvertor` | Convert thumbnail format |
| `FFmpegSplitChaptersPP` | `FFmpegSplitChapters` | Split by chapters |
| `FFmpegConcatPP` | `FFmpegConcat` | Concatenate files |
| `FFmpegCopyStreamPP` | `FFmpegCopyStream` | Copy streams |
| `FFmpegFixup*PP` | Various | Fix container issues |
| `EmbedThumbnailPP` | `EmbedThumbnail` | Embed thumbnail as cover art |
| `ExecPP` | `Exec` | Run external command |
| `MetadataParserPP` | `MetadataParser` | Parse/modify metadata |
| `MetadataFromFieldPP` | `MetadataFromField` | Extract metadata from fields |
| `ModifyChaptersPP` | `ModifyChapters` | Add/remove chapters |
| `MoveFilesAfterDownloadPP` | `MoveFilesAfterDownload` | Move files to final path |
| `SponsorBlockPP` | `SponsorBlock` | SponsorBlock integration |
| `XAttrMetadataPP` | `XAttrMetadata` | Write xattrs |

### PP Key Convention
The `key` for `--use-postprocessor` or the `postprocessors` param is the class name minus the `PP` suffix, and for FFmpeg PPs, also minus the `FFmpeg` prefix. So `FFmpegExtractAudioPP` has key `ExtractAudio`.

### PP Registration via `get_postprocessor(key)` (`postprocessor/__init__.py:51`)
```python
def get_postprocessor(key):
    return postprocessors.value[key + 'PP']
```

## Plugin System (`plugins.py`)

### Architecture
- Plugins are namespace packages under `yt_dlp_plugins.extractor` and `yt_dlp_plugins.postprocessor`
- `PluginSpec` dataclass defines: `module_name`, `suffix` (`IE` or `PP`), `destination`, `plugin_destination`
- All public classes ending in `IE`/`PP` are auto-imported
- Private classes (underscore prefix) and `__all__` are respected
- Plugin extractors override built-in ones via `plugin_name` class kwarg

### Plugin Locations (searched in order)
1. Config directories: `${XDG_CONFIG_HOME}/yt-dlp/plugins/<pkg>/yt_dlp_plugins/`
2. Executable directory: `<root>/yt-dlp-plugins/<pkg>/yt_dlp_plugins/`
3. `PYTHONPATH` / pip-installed packages
4. `.zip`, `.egg`, `.whl` archives

Disable all plugins: `YTDLP_NO_PLUGINS=1`

### Global State (`globals.py`)
Uses `Indirect` pattern (thread-safe context var wrapper) for:
- `extractors` — all registered extractors
- `plugin_ies` — plugin extractors
- `plugin_ies_overrides` — plugin overrides
- `plugin_pps` — plugin postprocessors
- `postprocessors` — all registered PPs
- `all_plugins_loaded` — flag
- `plugin_dirs` — search directories
- `IN_CLI` — whether running from CLI
- `LAZY_EXTRACTORS` — lazy loading flag

## Downloader System

Downloaders in `downloader/`:
- `http.py` — HTTP/HTTPS downloads with resume support
- `hls.py` — HLS/m3u8 native downloader
- `external.py` — wraps aria2c, axel, curl, ffmpeg, httpie, wget
- `rtmp.py` — RTMP via rtmpdump

`get_suitable_downloader(info_dict, params)` selects the right one.

## Networking

- `networking/common.py` — `RequestDirector` and request handler base
- `networking/impersonate.py` — browser impersonation via curl_cffi
- Supports custom headers, proxies, client certificates, TLS fingerprinting

## JavaScript Runtime System (`utils/_jsruntime.py`)

Supports Deno, Node.js, Bun, QuickJS for:
- YouTube signature decryption
- N-parameter transformation
- Player client operations

Configurable via `js_runtimes` param.

## Dependencies (`pyproject.toml:48-59`)

Required: Python >= 3.10
Optional (`[default]`):
- `brotli`/`brotlicffi` — Brotli compression
- `certifi` — TLS certificates
- `mutagen` — Audio metadata
- `pycryptodomex` — Crypto operations
- `requests` — HTTP client
- `urllib3` — HTTP library
- `websockets` — WebSocket support
- `yt-dlp-ejs` — External JS components

Optional extras:
- `curl-cffi` — Browser impersonation
- `secretstorage` — Linux keyring
- `deno` — Deno JS runtime
