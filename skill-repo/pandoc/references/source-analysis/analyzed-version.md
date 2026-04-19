# Analyzed Version

## Version

| Field | Value |
|---|---|
| Package | pandoc |
| Version analyzed | 3.9.0.2 |
| Git tag | c15e062 (untagged tip — release tag for 3.9.0.2 not present in shallow clone) |
| Git commit | c15e0628670e08eb1d92a412d779ef0dc687f58c |
| Date analyzed | 2026-04-19 |
| Release date | 2026-03-19 |
| License | GPL-2.0-or-later |

## Installation

| Field | Value |
|---|---|
| Installed binary | `C:\Program Files\Pandoc\pandoc.exe` |
| Installed version | 3.9.0.2 |
| Features | `+server +lua` |
| Scripting engine | Lua 5.4 |
| User data dir | `C:\Users\jeffr\AppData\Roaming\pandoc` |

The installed binary version (3.9.0.2) matches the source HEAD version declared in `pandoc.cabal` and `pandoc-cli/pandoc-cli.cabal`. The shallow clone HEAD is the 3.9.0.2 release commit; `git describe` returns `c15e062` because release tags were not fetched.

There is no detected divergence between source and installed binary. All flags listed by `pandoc --help` against the installed 3.9.0.2 binary appear in `src/Text/Pandoc/App/CommandLineOptions.hs` at the analyzed commit, and vice versa.

## Source

- Repository: https://github.com/jgm/pandoc
- Source analyzed at: `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc`
- Release notes: `changelog.md` at repo root (entry for 3.9.0.2 dated 2026-03-19)

## Package layout (top-level)

The repo is a multi-package Cabal project:

- `pandoc` — the library (`pandoc.cabal`, src under `src/Text/Pandoc/`)
- `pandoc-cli` — the CLI executable (`pandoc-cli/pandoc-cli.cabal`, entry point `pandoc-cli/src/pandoc.hs`)
- `pandoc-lua-engine` — the Lua scripting engine (`pandoc-lua-engine/src/Text/Pandoc/Lua/`)
- `pandoc-server` — HTTP server (`pandoc-server/`)
- `citeproc` — vendored copy of citeproc library
- `xml-light` — vendored XML library

The CLI binary depends on all of the above; the Lua engine and server are gated behind cabal flags (`flag lua`, `flag server`, both default `True`).

## Bundled data

The `data/` directory ships with the binary and provides:

- `data/templates/` — 61 default templates (one per output format, e.g. `default.html5`, `default.latex`, `default.docx` is a binary in `data/docx/`)
- `data/translations/` — 107 YAML translation files (one per language) for template strings like "Figure", "Table", "Abstract"
- `data/default.csl` — fallback citation style (Chicago author-date). There is no `data/csl/` subdirectory; this is a single file at the root of `data/`.
- `data/abbreviations` — default English abbreviations file (used by `--abbreviations`)
- `data/init.lua` and `data/creole.lua` — built-in Lua scaffolding
- `data/docx/`, `data/odt/`, `data/pptx/`, `data/dzslides/` — reference-doc skeletons for binary writers

Pandoc resolves data files via the user data dir first, then falls back to the bundled `data/`. Override with `--data-dir`.

## Build configuration

The CLI binary is built from `pandoc-cli/pandoc-cli.cabal` and pulls in the library at exact version (`pandoc == 3.9.0.2`, `pandoc-cli/pandoc-cli.cabal:72`). Build-time cabal flags:

| Flag | Default | Effect |
|---|---|---|
| `lua` | True | Pulls `pandoc-lua-engine`; enables `--lua-filter`. Reflected in `--version` features list as `+lua`. |
| `server` | True | Pulls `pandoc-server`, `wai-extra`, `warp`; enables `pandoc server` subcommand. Reflected as `+server`. |
| `repl` | True | Pulls `hslua-cli`; enables Lua REPL. |
| `nightly` | False | Adds `-nightly-COMPILEDATE` to `--version` output. |

The installed Windows binary at `C:\Program Files\Pandoc\pandoc.exe` was built with `+lua +server` (confirmed via `--version`). REPL and nightly are not advertised separately.

GHC compatibility: tested with GHC 9.6.7, 9.8.4, 9.10.3, 9.12.2 (`pandoc.cabal:14`).

## Key dependencies

The library has many dependencies; the ones most relevant to the wrapper's behavior:

| Dependency | Role |
|---|---|
| `pandoc-types` | The AST (`Pandoc`, `Block`, `Inline`, `Meta`) — separate package, https://hackage.haskell.org/package/pandoc-types |
| `doctemplates` | Template engine (`$variable$`, `$if$`, `$for$`) |
| `citeproc` | CSL processor used by `--citeproc` |
| `skylighting` | Syntax highlighting (KDE syntax XMLs); supplies `--list-highlight-styles` and `--list-highlight-languages` |
| `texmath` | Math conversion (LaTeX ↔ MathML ↔ OMML ↔ Typst) |
| `pandoc-lua-engine` | Lua filter execution (when `+lua`) |
| `pandoc-server` | HTTP server mode (when `+server`) |
| `typst` | Typst writer + Typst-based PDF generation |
| `djot` | Djot reader/writer |
| `commonmark-pandoc` | CommonMark/GFM reader |

## What's new in 3.9.x (relative to 3.8)

Highlights from `changelog.md` (entries for 3.9, 3.9.0.1, 3.9.0.2):

- **WASM build** — pandoc can be compiled to WASM and run in a browser; bundled GUI at https://pandoc.org/app (3.9 release)
- **Defaults files may be JSON or YAML** — JSON form is isomorphic to YAML form (3.9)
- **Variable expansion in `defaults` field** of defaults files
- **`--extract-media=foo.zip`** now produces a zip archive instead of a directory
- **Citeproc**: `reset-citation-positions` class on a top-level heading resets first-citation tracking — useful for chapter-based docs
- **Markdown reader**: `alerts` extension (GFM-style alerts), tighter inline-math parsing
- New writer dialects: `bbcode_steam`, `bbcode_phpbb`, `bbcode_fluxbb`, `bbcode_hubzilla`, `bbcode_xenforo`, plus `vimdoc` and `pod`
- **Lua API**: `pandoc.types.Sources` added (3.9.0.2)
- 3.9.0.2 specifically is a small follow-up: Typst template regression fix (#11538), docx-reader fixes for media handling, Markdown writer escape-of-`&` fix

No flags were added or removed between 3.8 and 3.9.0.2 in a way that affects this wrapper's MVP scope.

## Sources

- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\pandoc.cabal`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\pandoc-cli\pandoc-cli.cabal`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\changelog.md` (line 3 — release entry for 3.9.0.2; line 194 — 3.9 release notes)
- https://github.com/jgm/pandoc/blob/main/pandoc.cabal
- https://github.com/jgm/pandoc/blob/main/pandoc-cli/pandoc-cli.cabal
- https://github.com/jgm/pandoc/blob/main/changelog.md
- https://pandoc.org/releases.html
- https://hackage.haskell.org/package/pandoc-types
- https://hackage.haskell.org/package/citeproc
- https://hackage.haskell.org/package/skylighting
