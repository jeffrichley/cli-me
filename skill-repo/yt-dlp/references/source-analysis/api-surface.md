# yt-dlp API Surface Analysis

Source: `yt-dlp` v2026.03.17 (`yt_dlp/version.py:3`)

## Entry Points

### CLI Entry Point
- `pyproject.toml:138` defines `yt-dlp = "yt_dlp:main"`
- `yt_dlp/__init__.py:1076` — `main(argv=None)` sets `IN_CLI.value = True`, calls `_real_main(argv)`
- `yt_dlp/__init__.py:963` — `_real_main(argv=None)` parses options, creates `YoutubeDL`, calls `ydl.download(urls)`

### Python API Entry Point
```python
from yt_dlp import YoutubeDL

with YoutubeDL(params) as ydl:
    ydl.download(url_list)
```

The `YoutubeDL` class is the sole public API. It is a context manager.

## YoutubeDL Class (`yt_dlp/YoutubeDL.py:199`)

### Constructor
```python
YoutubeDL(params=None, auto_init=True)
```
- `params`: dict of options (see params dict below)
- `auto_init`: whether to load default extractors and print verbose header. Set to `'no_verbose_header'` to suppress header.

### Key Public Methods

| Method | Line | Signature | Description |
|--------|------|-----------|-------------|
| `extract_info` | 1643 | `(url, download=True, ie_key=None, extra_info=None, process=True, force_generic_extractor=False)` | Extract info dict from URL. Set `download=False` for metadata only. |
| `download` | 3659 | `(url_list)` | Download a list of URLs. Accepts single URL string too. Returns retcode. |
| `download_with_info_file` | 3675 | `(info_filename)` | Download using a previously saved `.info.json` file. |
| `process_info` | 3298 | `(info_dict)` | Process a single resolved IE result (downloads the video). |
| `process_ie_result` | 1876 | `(ie_result, download=True, extra_info=None)` | Process an info extractor result (playlist or video). |
| `prepare_filename` | 1523 | `(info_dict, dir_type='', *, outtmpl=None, warn=False)` | Generate output filename from template. |
| `build_format_selector` | 2304 | `(format_spec)` | Parse format selection string into a selector function. |
| `add_info_extractor` | 898 | `(ie)` | Register an info extractor. |
| `add_postprocessor` | (via `add_post_processor`) | `(pp, when='post_process')` | Register a postprocessor at a specific stage. |
| `add_progress_hook` | 951 | `(ph)` | Register a download progress callback. |
| `add_postprocessor_hook` | 955 | `(ph)` | Register a postprocessor progress callback. |
| `urlopen` | 4239 | `(req)` | Open a URL request (internal networking). |
| `sanitize_info` | 3697 | `(info_dict, remove_private_keys=False)` | Static method. Make info_dict JSON-serializable. |
| `to_screen` | 992 | `(message, skip_eol=False, quiet=None, only_once=False)` | Print message to screen. |
| `report_warning` | 1128 | `(message, only_once=False)` | Print warning message. |
| `report_error` | 1149 | `(message, *args, **kwargs)` | Print error message. |

### Params Dict (Complete Reference)

Defined in the docstring at `YoutubeDL.py:224-591`. Key groups:

#### Authentication
| Param | Type | Description |
|-------|------|-------------|
| `username` | str | Username for authentication |
| `password` | str | Password for authentication |
| `videopassword` | str | Password for accessing a video |
| `usenetrc` | bool | Use netrc for authentication |
| `netrc_location` | str | Location of netrc file (default: `~/.netrc`) |
| `netrc_cmd` | str | Shell command to get credentials |
| `cookiefile` | str | Cookie file path |
| `cookiesfrombrowser` | tuple | Browser cookie source, e.g. `('chrome',)` |

#### Format Selection
| Param | Type | Description |
|-------|------|-------------|
| `format` | str/func | Format code string OR a function `(ctx) -> formats` |
| `format_sort` | list[str] | Fields to sort formats by |
| `format_sort_force` | bool | Force user sort order over defaults |
| `prefer_free_formats` | bool | Prefer free containers |
| `allow_multiple_video_streams` | bool | Allow merging multiple video streams |
| `allow_multiple_audio_streams` | bool | Allow merging multiple audio streams |
| `check_formats` | bool/str/None | Test if formats are downloadable |
| `merge_output_format` | str | `/`-separated list of merge extensions |

#### Output
| Param | Type | Description |
|-------|------|-------------|
| `outtmpl` | dict | Templates keyed by type: `default`, `subtitle`, `thumbnail`, `description`, `infojson`, etc. |
| `outtmpl_na_placeholder` | str | Placeholder for unavailable fields (default: `"NA"`) |
| `paths` | dict | Output paths: `home`, `temp`, and OUTTMPL_TYPES keys |
| `restrictfilenames` | bool | ASCII-only filenames |
| `windowsfilenames` | bool | Windows-compatible filenames |
| `trim_file_name` | int | Max filename length |

#### Download Control
| Param | Type | Description |
|-------|------|-------------|
| `skip_download` | bool | Skip actual download |
| `simulate` | bool | Do not download or write to disk |
| `ignoreerrors` | bool/str | `True`, `False`, or `'only_download'` |
| `download_archive` | set/str | Archive file/set for tracking downloads |
| `break_on_existing` | bool | Stop on archived video |
| `max_downloads` | int | Abort after N downloads |
| `daterange` | DateRange | Only download within date range |
| `age_limit` | int | Skip videos unsuitable for age |
| `match_filter` | func | `(info_dict, *, incomplete) -> Optional[str]` |
| `playlist_items` | str | Specific playlist indices |
| `noplaylist` | bool | Single video mode |
| `extract_flat` | bool/str | `False`, `True`, `'in_playlist'`, `'discard'`, `'discard_in_playlist'` |

#### Postprocessing
| Param | Type | Description |
|-------|------|-------------|
| `postprocessors` | list[dict] | Each dict has `key` (PP name) and `when` (stage) |
| `ffmpeg_location` | str | Path to ffmpeg binary |
| `postprocessor_args` | dict | Args per PP/executable |

#### Networking
| Param | Type | Description |
|-------|------|-------------|
| `proxy` | str | Proxy URL |
| `source_address` | str | Client-side IP to bind to |
| `impersonate` | ImpersonateTarget | Browser to impersonate |
| `http_headers` | dict | Custom HTTP headers |
| `socket_timeout` | float | Timeout in seconds |
| `external_downloader` | dict | Protocol-to-downloader mapping |

#### Callbacks
| Param | Type | Description |
|-------|------|-------------|
| `progress_hooks` | list[func] | Download progress callbacks |
| `postprocessor_hooks` | list[func] | PP progress callbacks |
| `logger` | object | Object with `debug`, `warning`, `error` methods |

#### Sleep/Rate
| Param | Type | Description |
|-------|------|-------------|
| `sleep_interval` | float | Seconds before each download |
| `max_sleep_interval` | float | Upper bound for random sleep |
| `sleep_interval_requests` | float | Between extraction requests |
| `sleep_interval_subtitles` | float | Before subtitle downloads |
| `ratelimit` | int | Max download rate (bytes/sec) |

#### Extractor Config
| Param | Type | Description |
|-------|------|-------------|
| `extractor_retries` | int | Retries for known errors (default: 3) |
| `extractor_args` | dict | Per-extractor arguments, e.g. `{'youtube': {'skip': ['dash']}}` |
| `allowed_extractors` | list | Regex list of allowed extractors |

## Embedding Examples (from README lines 2054-2249)

### Basic download
```python
from yt_dlp import YoutubeDL
with YoutubeDL() as ydl:
    ydl.download(['https://www.youtube.com/watch?v=BaW_jenozKc'])
```

### Extract metadata only
```python
import json, yt_dlp
with yt_dlp.YoutubeDL({}) as ydl:
    info = ydl.extract_info(URL, download=False)
    print(json.dumps(ydl.sanitize_info(info)))
```

### Extract audio with postprocessor
```python
ydl_opts = {
    'format': 'm4a/bestaudio/best',
    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a'}],
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download(URLS)
```

### Custom format selector function
```python
def format_selector(ctx):
    formats = ctx.get('formats')[::-1]
    best_video = next(f for f in formats if f['vcodec'] != 'none' and f['acodec'] == 'none')
    audio_ext = {'mp4': 'm4a', 'webm': 'webm'}[best_video['ext']]
    best_audio = next(f for f in formats if f['acodec'] != 'none' and f['vcodec'] == 'none' and f['ext'] == audio_ext)
    yield {
        'format_id': f'{best_video["format_id"]}+{best_audio["format_id"]}',
        'ext': best_video['ext'],
        'requested_formats': [best_video, best_audio],
        'protocol': f'{best_video["protocol"]}+{best_audio["protocol"]}',
    }

ydl_opts = {'format': format_selector}
```

### Custom postprocessor
```python
class MyCustomPP(yt_dlp.postprocessor.PostProcessor):
    def run(self, info):
        self.to_screen('Doing stuff')
        return [], info  # (list_of_files_to_delete, info_dict)

with yt_dlp.YoutubeDL() as ydl:
    ydl.add_post_processor(MyCustomPP(), when='pre_process')
    ydl.download(URLS)
```

### Logger and progress hooks
```python
class MyLogger:
    def debug(self, msg): pass   # info messages also go here (prefix '[debug] ' for actual debug)
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(msg)

def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now post-processing ...')

ydl_opts = {'logger': MyLogger(), 'progress_hooks': [my_hook]}
```

## Progress Hook Dict Fields

For download hooks (`status` = `"downloading"` or `"finished"`):
- `status`, `info_dict`, `filename`, `tmpfilename`
- `downloaded_bytes`, `total_bytes`, `total_bytes_estimate`
- `elapsed`, `eta`, `speed`
- `fragment_index`, `fragment_count`

For postprocessor hooks:
- `status`: `"started"`, `"processing"`, `"finished"`
- `postprocessor`: PP name
- `info_dict`

## CLI-to-API Translation Tool
`devscripts/cli_to_api.py` — translates CLI flags to YoutubeDL params dict.
