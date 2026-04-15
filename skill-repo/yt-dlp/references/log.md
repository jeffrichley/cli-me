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
