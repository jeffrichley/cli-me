# yt-dlp Knowledge Base Log

## 2026-04-15: Initial research completed

Analyzed yt-dlp v2026.03.17 (stable channel). Created:
- 5 source analysis pages (version, API surface, CLI interface, architecture, key functions)
- 10 technique pages covering all major yt-dlp workflows
- Index, gotchas, and this log file

Source repo: https://github.com/yt-dlp/yt-dlp (shallow clone at commit 2c28ee5)

## 2026-04-15: Adversarial review and URL fixes

- Adversarial wiki reviewer (R1) found 8 factual errors across 6 technique pages
- Fixed all objective failures:
  - post-processing.md: SponsorBlock uses stream copy, not re-encoding
  - output-templates.md: `--windows-filenames` restricts characters, doesn't replace spaces
  - format-selection.md: Numeric fields use numeric comparison, not string
  - format-selection.md: Removed rate-limit claim (belongs in network page)
  - authentication.md: Cookie line endings handled automatically by yt-dlp
  - batch-operations.md: Config files expand `~` but not `$HOME`
- Removed dead source URLs (jnzlab.com, ostechnix.com, mariovillalobos.com)
- Removed misattributed DeepWiki source (documented Rust wrapper, not CLI)
- Remaining "dead" URLs are example placeholders in code blocks (not source citations)

## 2026-04-15: CLI implementation completed

Built agent-native CLI with 5 command groups, 18 commands:
- download: video, audio, playlist, channel
- info: formats, metadata, subtitles, thumbnails
- process: sponsorblock, chapters, remux, embed
- batch: from-file, sync, search
- config: cookies, archive-check, archive-add

Test results: 134 tests passed (132 Tier 1 command-graph + 2 Tier 2 integration)

## 2026-04-15: Full adversarial review — all findings addressed

Ran `/adversarial-review yt-dlp` (5 parallel reviewers + 3 static checks).
Found 15 objective failures and 14 judgment calls. All addressed:

Critical fixes:
- Added yt_dlp_cli.py shim script (CLI was completely non-functional as documented)
- Fixed config_cookies browser spec bug (+ for keyring, :: for container)
- Corrected CRLF/LF cookie guidance (line endings DO matter per yt-dlp FAQ)
- Fixed --retry-sleep example syntax (needs type prefix)

Alignment fixes:
- Documented --force-overwrites default in SKILL.md and gotchas.md
- Fixed channel output template (readable date format + video ID for dedup)
- Documented audio quality named levels (best/high/medium/low/worst)
- Added sponsorblock no-op warning

Test hardening (14 tests strengthened, 9 added → 148 total):
- Fixed systemic adjacency check weakness (-N/-r values swappable undetected)
- Fixed 6 presence-only tests (checked flag but not value)
- Added missing parameter tests for download_channel and download_playlist

Wiki improvements:
- Warned about embed-subs silently failing on audio containers
- Added Windows note to --exec examples
- Added illegal filename character warning for Windows
- Fixed ? operator example in format-selection
- Softened unsourced 30-minute Cloudflare claim
- Added Instagram/Vimeo/Twitch trigger phrases
