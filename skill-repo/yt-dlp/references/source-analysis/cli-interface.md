# yt-dlp CLI Interface Analysis

Source: `yt_dlp/options.py` (parser at line 247), README.md lines 355-1076

## Invocation

```
yt-dlp [OPTIONS] URL [URL...]
```

Entry point: `yt_dlp:main` (pyproject.toml:138)

## Option Groups

The CLI is organized into 16 option groups (options.py:1986-2001):

1. **General Options**
2. **Network Options**
3. **Geo-restriction**
4. **Video Selection**
5. **Download Options**
6. **Filesystem Options**
7. **Thumbnail Options**
8. **Internet Shortcut Options**
9. **Verbosity and Simulation Options**
10. **Workarounds**
11. **Video Format Options**
12. **Subtitle Options**
13. **Authentication Options**
14. **Post-processing Options**
15. **SponsorBlock Options**
16. **Extractor Options**

Plus a dynamic **Aliases** group and **Preset Aliases**.

## Most Important CLI Flags (Grouped)

### Core / General
| Flag | Description |
|------|-------------|
| `-h, --help` | Print help |
| `--version` | Print version |
| `-U, --update` | Update to latest version |
| `-i, --ignore-errors` | Continue on errors |
| `--list-extractors` | List all extractors |
| `--use-extractors NAME` | Use specific extractors |
| `--default-search PREFIX` | Prefix for unqualified URLs |
| `--ignore-config` | Skip config files |
| `--config-locations PATH` | Custom config file location |
| `--plugin-dirs DIR` | Additional plugin directories |

### Format Selection
| Flag | Description |
|------|-------------|
| `-f, --format FORMAT` | Format selector expression |
| `-S, --format-sort FIELDS` | Sort format preference |
| `--format-sort-force` | Override extractor sort |
| `-F, --list-formats` | List available formats |
| `--merge-output-format FMT` | Container for merged output |
| `--video-multistreams` | Allow multiple video streams |
| `--audio-multistreams` | Allow multiple audio streams |
| `--prefer-free-formats` | Prefer free containers |
| `--check-formats` | Verify format availability |

### Output / Filesystem
| Flag | Description |
|------|-------------|
| `-o, --output [TYPE:]TMPL` | Output filename template |
| `-P, --paths [TYPE:]PATH` | Output directory paths |
| `--output-na-placeholder` | Placeholder for missing fields |
| `--restrict-filenames` | ASCII-only filenames |
| `-w, --no-overwrites` | Never overwrite |
| `--force-overwrites` | Always overwrite |
| `-c, --continue` | Resume partial downloads |
| `-a, --batch-file FILE` | Read URLs from file |
| `--cookies FILE` | Netscape cookie file |
| `--cookies-from-browser BROWSER` | Load cookies from browser |
| `--write-info-json` | Save metadata to JSON |
| `--write-description` | Save description file |
| `--write-comments` | Include comments in infojson |
| `--load-info-json FILE` | Resume from info JSON |
| `--download-archive FILE` | Skip previously downloaded |
| `--cache-dir DIR` | Cache directory |

### Download Control
| Flag | Description |
|------|-------------|
| `-N, --concurrent-fragments N` | Parallel fragment downloads |
| `-r, --limit-rate RATE` | Bandwidth limit (e.g. `50K`) |
| `-R, --retries N` | Download retries |
| `--fragment-retries N` | Fragment-level retries |
| `--retry-sleep [TYPE:]EXPR` | Sleep between retries |
| `--download-sections REGEX` | Download specific chapters/time ranges |
| `--downloader [PROTO:]NAME` | External downloader |
| `--playlist-random` | Randomize playlist order |
| `--lazy-playlist` | Stream playlist entries |
| `-I, --playlist-items SPEC` | Select playlist indices |

### Video Selection / Filtering
| Flag | Description |
|------|-------------|
| `--date DATE` | Videos from this date only |
| `--datebefore / --dateafter` | Date range filtering |
| `--match-filters FILTER` | Filter on any output template field |
| `--break-match-filters` | Stop on filter rejection |
| `--no-playlist` | Single video only |
| `--age-limit YEARS` | Age restriction filter |
| `--max-downloads N` | Stop after N downloads |
| `--break-on-existing` | Stop on archived video |
| `--min-filesize / --max-filesize` | File size limits |

### Verbosity / Simulation
| Flag | Description |
|------|-------------|
| `-q, --quiet` | Quiet mode |
| `-s, --simulate` | Don't download |
| `--skip-download` | Write metadata files only |
| `-O, --print [WHEN:]TMPL` | Print template to stdout |
| `--print-to-file [WHEN:]TMPL FILE` | Append template to file |
| `-j, --dump-json` | Print info JSON per video |
| `-J, --dump-single-json` | Print info JSON for URL/playlist |
| `-v, --verbose` | Debug output |
| `--progress-template TYPE:TMPL` | Customize progress display |
| `--no-progress` | Hide progress bar |

### Thumbnails
| Flag | Description |
|------|-------------|
| `--write-thumbnail` | Save thumbnail |
| `--write-all-thumbnails` | Save all thumbnail formats |
| `--list-thumbnails` | List available thumbnails |

### Subtitles
| Flag | Description |
|------|-------------|
| `--write-subs` | Download subtitles |
| `--write-auto-subs` | Download auto-generated subs |
| `--list-subs` | List available subtitles |
| `--sub-format FMT` | Subtitle format preference |
| `--sub-langs LANGS` | Language codes (supports regex, `all`) |

### Authentication
| Flag | Description |
|------|-------------|
| `-u, --username` | Account username |
| `-p, --password` | Account password |
| `--netrc` | Use .netrc file |
| `--netrc-location` | Custom .netrc path |
| `--netrc-cmd` | Shell command for creds |
| `--ap-mso / --ap-username / --ap-password` | Adobe Pass TV Provider |
| `--client-certificate` | TLS client cert |

### Post-Processing
| Flag | Description |
|------|-------------|
| `-x, --extract-audio` | Convert to audio-only |
| `--audio-format FMT` | Target audio format |
| `--audio-quality QUALITY` | Audio quality (0=best, 10=worst, or kbps) |
| `--remux-video FMT` | Remux to container |
| `--recode-video FMT` | Re-encode to format |
| `--embed-subs` | Embed subtitles in video |
| `--embed-thumbnail` | Embed thumbnail as cover art |
| `--embed-metadata` | Embed metadata tags |
| `--embed-chapters` | Embed chapter markers |
| `--embed-info-json` | Embed info.json in file |
| `--parse-metadata FROM:TO` | Modify metadata fields |
| `--replace-in-metadata FIELDS REGEX REPLACE` | Regex replace in metadata |
| `--convert-subs FMT` | Convert subtitle format |
| `--convert-thumbnails FMT` | Convert thumbnail format |
| `--split-chapters` | Split by internal chapters |
| `--remove-chapters REGEX` | Remove matching chapters |
| `--fixup POLICY` | Auto-fix file issues |
| `--ffmpeg-location PATH` | Path to ffmpeg |
| `--exec [WHEN:]CMD` | Run command after download |
| `--use-postprocessor NAME[:ARGS]` | Use custom PP |
| `--postprocessor-args NAME:ARGS` | Pass args to PP |

### SponsorBlock
| Flag | Description |
|------|-------------|
| `--sponsorblock-mark CATS` | Mark sponsor segments as chapters |
| `--sponsorblock-remove CATS` | Remove sponsor segments |
| `--sponsorblock-chapter-title TMPL` | Chapter title template |

### Extractor
| Flag | Description |
|------|-------------|
| `--extractor-retries N` | Retries for extractor errors |
| `--extractor-args KEY:ARGS` | Per-extractor arguments |

### Network
| Flag | Description |
|------|-------------|
| `--proxy URL` | Proxy server |
| `--socket-timeout SECS` | Socket timeout |
| `--source-address IP` | Bind address |
| `--impersonate CLIENT[:OS]` | Browser impersonation |
| `-4 / -6` | Force IPv4/IPv6 |
| `--enable-file-urls` | Allow `file://` |

### Workarounds
| Flag | Description |
|------|-------------|
| `--legacy-server-connect` | Allow insecure renegotiation |
| `--no-check-certificates` | Skip SSL verification |
| `--add-headers FIELD:VALUE` | Custom HTTP headers |
| `--sleep-requests SECS` | Sleep between requests |
| `--sleep-interval SECS` | Sleep before downloads |
| `--max-sleep-interval SECS` | Max random sleep |

## Configuration File Locations

Config is loaded from (options.py:82-87, README):
1. Portable: `<executable-dir>/yt-dlp.conf`
2. Home: path set by `--paths home:`
3. User: `${XDG_CONFIG_HOME}/yt-dlp/config` or `${APPDATA}/yt-dlp/config`
4. System: `/etc/yt-dlp/config`

## Output Template System

Template syntax: `%(field_name)s` with extensions:
- Object traversal: `%(tags.0)s`, `%(subtitles.en.-1.ext)s`
- Arithmetic: `%(playlist_index+10)03d`
- Date formatting: `%(upload_date>%Y-%m-%d)s`
- Alternatives: `%(release_date>%Y,upload_date>%Y|Unknown)s`
- Replacement: `%(chapters&has chapters|no chapters)s`
- Default: `%(uploader|Unknown)s`
- Extra conversions: `B` (bytes), `j` (json), `h` (html), `l` (list), `q` (shell-quoted), `D` (decimal suffix), `S` (sanitize), `U` (unicode normalize)

General field syntax:
```
%(name[.keys][addition][>strf][,alternate][&replacement][|default])[flags][width][.precision][length]type
```

### Output Template Types
Type-specific templates via `-o "TYPE:TEMPLATE"`:
`subtitle`, `thumbnail`, `description`, `annotation`, `infojson`, `link`, `pl_thumbnail`, `pl_description`, `pl_infojson`, `chapter`, `pl_video`

Default template: `%(title)s [%(id)s].%(ext)s`

## Format Selection Syntax

### Selectors
| Selector | Meaning |
|----------|---------|
| `b/best` | Best combined (video+audio) |
| `b*/best*` | Best with video OR audio |
| `bv/bestvideo` | Best video-only |
| `bv*/bestvideo*` | Best with video (may include audio) |
| `ba/bestaudio` | Best audio-only |
| `ba*/bestaudio*` | Best with audio |
| `w/worst` | Worst combined |
| `all` | All formats |
| `mergeall` | Merge all formats |

N-th best: `best.2`, `bv*.3`

### Operators
- `/` — fallback: `22/17/18`
- `,` — multiple formats: `22,17,18`
- `+` — merge: `bestvideo+bestaudio`

### Filters (in brackets)
Numeric: `<`, `<=`, `>`, `>=`, `=`, `!=` on `filesize`, `width`, `height`, `tbr`, `abr`, `vbr`, `asr`, `fps`, `audio_channels`, etc.

String: `=`, `^=`, `$=`, `*=`, `~=` on `ext`, `acodec`, `vcodec`, `protocol`, `language`, `format_id`, etc.

Negate with `!` prefix. Unknown values included with `?` suffix.

### Sort Fields (`-S`)
`hasvid`, `hasaud`, `ie_pref`, `lang`, `quality`, `source`, `proto`, `vcodec`, `acodec`, `codec`, `vext`, `aext`, `ext`, `filesize`, `fs_approx`, `size`, `height`, `width`, `res`, `fps`, `hdr`, `channels`, `tbr`, `vbr`, `abr`, `br`, `asr`

Prefix `+` for ascending, suffix `:VALUE` for preferred, `~VALUE` for nearest.

### Common Examples
```bash
yt-dlp -f "bv*+ba/b"                    # Best video+audio (default)
yt-dlp -f "bv[height<=720]+ba"          # Max 720p
yt-dlp -S "res:720,fps"                 # Best up to 720p, prefer high fps
yt-dlp -f "ba" -x --audio-format mp3    # Audio only as MP3
yt-dlp -f "bv*[ext=mp4]+ba[ext=m4a]"   # MP4 container
```
