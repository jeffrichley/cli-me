# yt-dlp Key Functions Reference

Source: yt-dlp v2026.03.17

## Core Workflow Functions

### `main(argv=None)` — `yt_dlp/__init__.py:1076`
CLI entry point. Sets `IN_CLI.value = True`, calls `_real_main(argv)`, handles exit codes.

### `_real_main(argv=None)` — `yt_dlp/__init__.py:963`
1. Parses options via `parse_options(argv)`
2. Handles `--list-extractors`, `--update`, `--rm-cache-dir`
3. Creates `YoutubeDL(ydl_opts)`
4. Calls `ydl.download(all_urls)` or `ydl.download_with_info_file()`

### `parse_options(argv)` — `yt_dlp/__init__.py` (called from _real_main)
Calls `parseOpts()` from `options.py`, validates options, builds the `ydl_opts` dict from CLI flags.

### `parseOpts()` — `yt_dlp/options.py:43`
Loads config from multiple sources (CLI, portable, home, user, system), returns parser + opts.

---

## YoutubeDL Core Methods

### `__init__(params=None, auto_init=True)` — `YoutubeDL.py:629`
- Initializes all internal state: `_ies`, `_pps`, progress hooks, download counter
- Sets up output streams, color handling, encoding
- If `auto_init=True`: loads default extractors, prints verbose header

### `extract_info(url, download=True, ie_key=None, ...)` — `YoutubeDL.py:1643`
Main extraction entry point.
1. Iterates registered extractors, finds first where `ie.suitable(url)` is True
2. Checks download archive for temp_id
3. Calls `__extract_info()` which invokes `ie._real_extract(url)`
4. Returns info_dict (may be playlist or video)

**Key params:**
- `download=False` — metadata extraction only (no file download)
- `ie_key='Youtube'` — force specific extractor
- `process=True` — resolve nested URLs/playlists

### `process_ie_result(ie_result, download=True, ...)` — `YoutubeDL.py:1876`
Routes result by `_type`:
- `'url'` or `'url_transparent'` — re-extract with resolved URL
- `'playlist'` or `'multi_video'` — iterate entries, call recursively
- `'video'` (default) — proceed to format selection and `process_info()`

### `build_format_selector(format_spec)` — `YoutubeDL.py:2304`
Parses format selection string (e.g. `"bv*+ba/b"`) into a callable selector function.
- Handles: selectors, filters `[height<=720]`, merge `+`, fallback `/`, comma `,`
- Returns a generator function that yields format dicts

### `process_info(info_dict)` — `YoutubeDL.py:3298`
Processes a single resolved video:
1. Checks match_filter
2. Runs `pre_process` PPs
3. Prepares filename from template
4. Writes subtitles, thumbnails, infojson, description, shortcut files
5. Downloads the actual video file
6. Runs `post_process` and `after_move` PPs
7. Checks max_downloads limit

### `download(url_list)` — `YoutubeDL.py:3659`
```python
def download(self, url_list):
    url_list = variadic(url_list)  # Single URL accepted
    for url in url_list:
        self.__download_wrapper(self.extract_info)(url, ...)
    return self._download_retcode
```

### `download_with_info_file(info_filename)` — `YoutubeDL.py:3675`
Reads `.info.json`, calls `process_ie_result()` for each entry. Falls back to re-extracting via URL.

### `prepare_filename(info_dict, dir_type='', ...)` — `YoutubeDL.py:1523`
Evaluates output template against info_dict, sanitizes the path, returns full filename.

### `sanitize_info(info_dict, remove_private_keys=False)` — `YoutubeDL.py:3697`
Static method. Adds `epoch`, `_type`, `_version`. Optionally removes private keys (`__`-prefixed, `requested_*`, etc.).

---

## Extractor System Functions

### `InfoExtractor.suitable(url)` — `extractor/common.py`
Class method. Tests URL against `_VALID_URL` regex.

### `InfoExtractor._real_extract(url)` — `extractor/common.py`
Override point. Returns info_dict with video metadata and formats.

### `gen_extractor_classes()` — `extractor/__init__.py:17`
Returns all registered extractors as a list. Triggers import of all extractors.

### `get_info_extractor(ie_name)` — `extractor/__init__.py:47`
Returns extractor class by name. E.g. `get_info_extractor('Youtube')` returns `YoutubeIE`.

### `import_extractors()` — `extractor/__init__.py:53`
Triggers import of all extractor modules (lazy loading).

---

## Postprocessor Functions

### `PostProcessor.run(info)` — `postprocessor/common.py:36`
Override point. Returns `(files_to_delete, info_dict)`. Wrapped by metaclass to fire progress hooks.

### `PostProcessor._restrict_to(*, video=True, audio=True, images=True, simulated=True)` — `postprocessor/common.py:114`
Decorator that skips PP execution for non-matching media types.

### `get_postprocessor(key)` — `postprocessor/__init__.py:51`
Looks up PP class by key name (appends `PP`). E.g. `get_postprocessor('FFmpegExtractAudio')`.

---

## Format Selection Functions

### `FormatSorter` — `utils/_utils.py`
Sorts available formats by configurable criteria. Default sort order:
```
lang,quality,res,fps,hdr:12,vcodec,channels,acodec,size,br,asr,proto,ext,hasaud,source,id
```

### Format Filter Operators
Applied inside `[]` in format selectors:
- Numeric: `<`, `<=`, `>`, `>=`, `=`, `!=`
- String: `=`, `^=`, `$=`, `*=`, `~=`
- Negate: `!` prefix
- Unknown-ok: `?` suffix (e.g. `height<=?720`)

---

## Output Template Functions

### `validate_outtmpl(tmpl)` — `YoutubeDL.py` (static)
Validates an output template string for syntax errors.

### Template Processing
Templates are evaluated in `prepare_filename()` using custom Python string formatting with extensions for:
- Object traversal: `%(tags.0)s`
- Arithmetic: `%(playlist_index+10)03d`
- Date formatting: `%(upload_date>%Y-%m-%d)s`
- Alternatives: `%(release_date,upload_date|Unknown)s`
- Special types: `j` (JSON), `l` (list), `q` (shell-quoted), `B` (bytes), `D` (decimal suffix), `S` (sanitized), `U` (unicode normalized)

### OUTTMPL_TYPES — `utils/_utils.py:2859`
```python
OUTTMPL_TYPES = {
    'chapter': None,
    'subtitle': None,
    'thumbnail': None,
    'description': 'description',
    'annotation': 'annotations.xml',
    'infojson': 'info.json',
    'link': None,
    'pl_video': None,
    'pl_thumbnail': None,
    'pl_description': 'description',
    'pl_infojson': 'info.json',
}
```

---

## Plugin System Functions

### `load_all_plugins()` — `plugins.py`
Discovers and imports all plugins from registered directories.

### `register_plugin_spec(spec)` — `plugins.py`
Registers a `PluginSpec` for auto-discovery. Called by `extractor/__init__.py` and `postprocessor/__init__.py`.

### `directories()` — `plugins.py`
Returns all directories searched for plugins (config dirs, executable dir, PYTHONPATH).

---

## Utility Functions (Most Used)

### `traverse_obj(obj, *paths, default=..., expected_type=..., get_all=True)` — `utils/traversal.py`
Deep getter for nested dicts/lists. Core utility used throughout extractors.

### `int_or_none(v, scale=1, default=None)` — `utils/_utils.py`
Safe int conversion. Returns None on failure.

### `float_or_none(v, scale=1, default=None)` — `utils/_utils.py`
Safe float conversion.

### `str_or_none(v, default=None)` — `utils/_utils.py`
Safe string conversion.

### `determine_ext(url, default_ext='unknown_video')` — `utils/_utils.py`
Extract file extension from URL.

### `sanitize_filename(s, restricted=False)` — `utils/_utils.py`
Make string safe for use as filename.

### `format_bytes(bytes)` — `utils/_utils.py`
Human-readable byte count (e.g. `"1.5MiB"`).

### `parse_duration(s)` — `utils/_utils.py`
Parse duration string to seconds.

### `unified_timestamp(date_str)` — `utils/_utils.py`
Parse various date formats to Unix timestamp.

### `clean_html(html)` — `utils/_utils.py`
Strip HTML tags and decode entities.

### `variadic(x)` — `utils/_utils.py`
Wraps non-list values in a list. Used to accept both single values and lists.

---

## Error Hierarchy

```
YoutubeDLError
    DownloadError
    SameFileError
    PostProcessingError
    MaxDownloadsReached
    UnavailableVideoError

ExtractorError (from InfoExtractor)
    GeoRestrictedError
    UnsupportedError

DownloadCancelled
    ExistingVideoReached
    RejectedVideoReached
    EntryNotInPlaylist

ContentTooShortError
CookieLoadError
```

---

## Key Constants

### `DEFAULT_OUTTMPL` — `utils/_utils.py`
```python
'%(title)s [%(id)s].%(ext)s'
```

### `MEDIA_EXTENSIONS` — `utils/_utils.py`
Contains `common_video`, `common_audio`, `storyboards` extension lists.

### `POSTPROCESS_WHEN` — `utils/_utils.py:2852`
```python
('pre_process', 'after_filter', 'video', 'before_dl', 'post_process', 'after_move', 'after_video', 'playlist')
```

### Extractor Arguments (per README lines 1852-1920)
Notable extractor-specific args:
- **youtube**: `player_client`, `skip`, `lang`, `comment_sort`, `max_comments`, `formats`, `po_token`, `player_skip`
- **generic**: `fragment_query`, `hls_key`, `is_live`, `impersonate`
