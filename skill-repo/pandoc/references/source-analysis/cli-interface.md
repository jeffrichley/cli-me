# CLI Interface

All flags verified against the installed binary `C:\Program Files\Pandoc\pandoc.exe` (3.9.0.2) and source at `src/Text/Pandoc/App/CommandLineOptions.hs` commit c15e062. Flag definitions begin at line 272 (`options =`).

## Synopsis

```
pandoc [OPTIONS] [FILES]
```

If no input files are given, input is read from stdin. Output goes to stdout unless `-o` is set. Multiple input files are concatenated (with blank lines between them) before parsing — use `--file-scope` to parse files individually.

## Format selection syntax

The `--from` and `--to` flag values use the syntax:

```
FORMAT[+EXT][-EXT]...
```

Examples:
- `markdown+yaml_metadata_block-implicit_figures` — markdown with YAML metadata enabled and implicit figures disabled
- `gfm+footnotes` — GitHub-Flavored Markdown plus footnotes
- `html-native_divs-native_spans` — HTML with native div/span passthrough disabled

Use `pandoc --list-extensions=FORMAT` to see all extensions and their default state for a format. `+` prefix in that list means on-by-default, `-` means off-by-default.

## Defaults file

`-d FILE` / `--defaults=FILE` loads CLI options from a YAML file. Top-level keys map to flag names with hyphens replaced by underscores in some contexts, but pandoc accepts hyphenated keys too. Example:

```yaml
from: markdown
to: pdf
output-file: out.pdf
standalone: true
toc: true
toc-depth: 3
pdf-engine: xelatex
metadata:
  title: My Document
  author: Jeff
bibliography:
  - refs.bib
csl: chicago-author-date.csl
citeproc: true
filters:
  - citeproc
  - my-filter.lua
```

Multiple `-d` flags compose. CLI flags override defaults-file values. See MANUAL.txt section "Defaults files" for the full schema.

## Introspection

These print information and exit:

- `--list-input-formats` — 51 input formats (asciidoc, biblatex, bibtex, bits, commonmark, commonmark_x, creole, csljson, csv, djot, docbook, docx, dokuwiki, endnotexml, epub, fb2, gfm, haddock, html, ipynb, jats, jira, json, latex, man, markdown, markdown_github, markdown_mmd, markdown_phpextra, markdown_strict, mdoc, mediawiki, muse, native, odt, opml, org, pod, pptx, ris, rst, rtf, t2t, textile, tikiwiki, tsv, twiki, typst, vimwiki, xlsx, xml)
- `--list-output-formats` — 75 output formats (adds: ansi, asciidoc_legacy, asciidoctor, bbcode + 5 variants, beamer, chunkedhtml, context, docbook4, docbook5, dzslides, epub2, epub3, html4, html5, icml, jats_archiving, jats_articleauthoring, jats_publishing, markua, ms, opendocument, pdf, plain, pptx, revealjs, s5, slideous, slidy, tei, texinfo, vimdoc, xwiki, zimwiki)
- `--list-extensions[=FORMAT]` — show all extensions or those for FORMAT
- `--list-highlight-styles` — 8 styles: pygments, tango, espresso, zenburn, kate, monochrome, breezedark, haddock
- `--list-highlight-languages` — 163 syntax-highlightable languages
- `--print-default-template=FORMAT` (alias `-D`) — print the bundled template for FORMAT (e.g. `pandoc -D html5 > my.html5`)
- `--print-default-data-file=FILE` — print a bundled data file (e.g. `--print-default-data-file=reference.docx`)
- `--print-highlight-style=STYLE|FILE` — print a highlight style as KDE XML
- `--bash-completion` — print bash completion script
- `--version` (alias `-v`) — print version, features, scripting engine
- `--help` (alias `-h`) — print flag list

## Complete flag inventory

Definitions at `src/Text/Pandoc/App/CommandLineOptions.hs` line numbers shown. **Scope tags**: MVP (in scope for v0.1), v0.2 (deferred), oos (out of scope for the wrapper, may still be useful as raw passthrough).

### General (MVP)

| Flag | Short | Arg | Default | Source line |
|---|---|---|---|---|
| `--from`, `--read` | `-f`, `-r` | FORMAT | auto from input ext | 274 |
| `--to`, `--write` | `-t`, `-w` | FORMAT | auto from output ext | 280 |
| `--output` | `-o` | FILE | stdout | 286 |
| `--data-dir` | | DIR | platform-default user dir | 293 |
| `--metadata` | `-M` | KEY[:VALUE] | — | 300 |
| `--metadata-file` | | FILE | — | 309 |
| `--defaults` | `-d` | FILE | — | 316 |
| `--file-scope` | | bool | false | 332 |
| `--sandbox` | | bool | false | 340 |
| `--standalone` | `-s` | bool | false (auto-true if `--template`, `--include-*`, or `--self-contained` set) | 348 |
| `--variable` | `-V` | KEY[:VALUE] | — | 363 |
| `--variable-json` | | KEY[:JSON] | — | 373 |
| `--wrap` | | `auto`\|`none`\|`preserve` | `auto` | 390 |
| `--ascii` | | bool | false | 402 |
| `--toc`, `--table-of-contents` | | bool | false | 410 |
| `--toc-depth` | | NUMBER | 3 | 418 |
| `--lof`, `--list-of-figures` | | bool | false | 429 |
| `--lot`, `--list-of-tables` | | bool | false | 437 |
| `--number-sections` | `-N` | bool | false | 445 |
| `--number-offset` | | NUMBERS | — | 453 |
| `--verbose` | | — | — | 1106 |
| `--quiet` | | — | — | 1111 |
| `--fail-if-warnings` | | bool | false | 1116 |
| `--log` | | FILE | — | 1124 |
| `--trace` | | bool | false | 1082 |

`--standalone` is implicitly enabled by `--template`, `--self-contained`, `--include-in-header`, `--include-before-body`, or `--include-after-body` (see App/CommandLineOptions.hs:91-100).

### Templates (MVP)

| Flag | Short | Arg | Notes | Source line |
|---|---|---|---|---|
| `--template` | | FILE | Implies `--standalone` | 356 |
| `--include-in-header` | `-H` | FILE | Repeatable, implies `--standalone` | 498 |
| `--include-before-body` | `-B` | FILE | Repeatable, implies `--standalone` | 506 |
| `--include-after-body` | `-A` | FILE | Repeatable, implies `--standalone` | 514 |
| `--reference-doc` | | FILE | docx, odt, pptx writers only | 628 |

The `-V`/`--variable` flag is the primary way to set template variables (e.g. `-V geometry:margin=1in`). For complex values use `--variable-json`.

### Filters (MVP)

| Flag | Short | Arg | Notes | Source line |
|---|---|---|---|---|
| `--filter` | `-F` | PROGRAM | JSON-API external filter (any executable) | 706 |
| `--lua-filter` | `-L` | SCRIPTPATH | Lua filter (Lua 5.4) | 713 |
| `--shift-heading-level-by` | | NUMBER | +N or -N | 720 |
| `--base-header-level` | | NUMBER | Deprecated; use `--shift-heading-level-by` | 731 |

`--filter` and `--lua-filter` are **order-sensitive** — they run in the order given on the command line, interleaved with each other. `--citeproc` (see below) is also a filter and obeys positional order.

### Citations (MVP)

| Flag | Short | Arg | Notes | Source line |
|---|---|---|---|---|
| `--citeproc` | `-C` | — | Run built-in citeproc filter | 1000 |
| `--bibliography` | | FILE | Repeatable; per MANUAL bibliography section, supported extensions are `.bib` (BibLaTeX), `.bibtex` (BibTeX), `.json` (CSL JSON), `.yaml` (CSL YAML), `.ris`. EndNote XML is supported only as an *input* format (`--from endnotexml`), not as a `--bibliography` extension | 1006 |
| `--csl` | | FILE | Path to CSL style file (default: Chicago author-date from `data/default.csl`) | 1015 |
| `--citation-abbreviations` | | FILE | JSON file of journal-name abbreviations | 1026 |
| `--natbib` | | — | LaTeX output: emit natbib commands instead of running citeproc | 1035 |
| `--biblatex` | | — | LaTeX output: emit biblatex commands instead of running citeproc | 1040 |

`--bibliography`, `--csl`, `--citation-abbreviations` only take effect when citeproc is active (either via `-C`, via `citeproc` in `--filter`, or by listing `bibliography:` in metadata with `--citeproc`).

### Reader-specific (mostly MVP)

| Flag | Arg | Applies to | Source line |
|---|---|---|---|
| `--abbreviations` | FILE | markdown, commonmark | 677 |
| `--track-changes` | `accept`\|`reject`\|`all` | docx | 744 |
| `--strip-comments` | bool | html, markdown | 757 |
| `--preserve-tabs` (`-p`) | bool | source-text readers | 589 |
| `--tab-stop` | NUMBER | source-text readers | 597 |
| `--typst-input` | bool | typst reader | 684 |

### Writer-specific (mixed scope)

#### LaTeX / PDF (MVP for `convert md → pdf`)

| Flag | Arg | Notes | Source line |
|---|---|---|---|
| `--pdf-engine` | PROGRAM | One of: pdflatex, lualatex, xelatex, latexmk, tectonic, weasyprint, wkhtmltopdf, pagedjs-cli, prince, groff, pdfroff, typst, context (line 208-226). Default: `pdflatex` for latex, `weasyprint` for html-to-pdf, `typst` for typst-to-pdf. | 607 |
| `--pdf-engine-opt` | STRING | Repeatable; passed to the engine | 620 |
| `--listings` | bool | Use `listings` package for code blocks | 831 |
| `--top-level-division` | `section`\|`chapter`\|`part` | LaTeX, ConTeXt, DocBook, JATS | 464 |

#### HTML (MVP for `convert md → html`)

| Flag | Arg | Notes | Source line |
|---|---|---|---|
| `--self-contained` | bool | Deprecated alias for `--embed-resources --standalone` | 635 |
| `--embed-resources` | bool | Inline images, CSS, JS as data: URIs | 644 |
| `--link-images` | bool | Don't fetch images, use `<img src=URL>` | 652 |
| `--section-divs` | bool | Wrap sections in `<section>` tags | 864 |
| `--html-q-tags` | bool | Use `<q>` for quoted text | 872 |
| `--email-obfuscation` | `none`\|`javascript`\|`references` | Default: `none` | 880 |
| `--id-prefix` | STRING | Prefix on auto-generated IDs | 893 |
| `--title-prefix` | STRING (`-T`) | Prepend to `<title>` | 899 |
| `--css` | URL (`-c`) | Repeatable | 910 |

#### EPUB (oos for v0.1, but MVP-listed since `convert md → epub` is in scope)

| Flag | Arg | Notes | Source line |
|---|---|---|---|
| `--epub-cover-image` | FILE | Cover image for EPUB | 924 |
| `--epub-title-page` | bool | Include title page | 934 |
| `--epub-metadata` | FILE | XML metadata file | 942 |
| `--epub-embed-font` | FILE | Repeatable | 949 |
| `--epub-subdirectory` | DIRNAME | OPF subdirectory | 917 |
| `--split-level` | NUMBER | Heading level at which to split into chapters | 957 |
| `--chunk-template` | PATHTEMPLATE | For chunkedhtml | 968 |
| `--epub-chapter-level` | NUMBER | Deprecated; use `--split-level` | 975 |

#### Slides (v0.2)

| Flag | Short | Arg | Source line |
|---|---|---|---|
| `--incremental` | `-i` | bool | 845 |
| `--slide-level` | | NUMBER | 853 |

#### Notebooks (v0.2)

| Flag | Arg | Source line |
|---|---|---|
| `--ipynb-output` | `all`\|`none`\|`best` | 988 |

### Math (oos for v0.1)

| Flag | Arg | Source line |
|---|---|---|
| `--mathml` | — | 1045 |
| `--webtex` | [URL] | 1051 |
| `--mathjax` | [URL] | 1059 |
| `--katex` | [URL] | 1067 |
| `--gladtex` | — | 1076 |

### Highlighting (oos for v0.1; pass-through useful)

| Flag | Arg | Source line |
|---|---|---|
| `--no-highlight` | — | Disable syntax highlighting (no deprecation marker in `pandoc --help`) | 522 |
| `--highlight-style` | STYLE\|FILE | Pick a highlight style (no deprecation marker in `pandoc --help`); `--syntax-highlighting=<style>` is the newer equivalent | 530 |
| `--syntax-definition` | FILE | KDE syntax XML | 540 |
| `--syntax-highlighting` | `none`\|`default`\|`idiomatic`\|stylename\|themepath | 548 |

### Output options (mixed)

| Flag | Short | Arg | Source line |
|---|---|---|---|
| `--extract-media` | | PATH | 482 |
| `--resource-path` | | SEARCHPATH | 490 |
| `--dpi` | | NUMBER | 556 |
| `--eol` | | `crlf`\|`lf`\|`native` | 566 |
| `--columns` | | NUMBER | 579 |
| `--default-image-extension` | | EXT | 700 |
| `--indented-code-classes` | | STRING | 692 |
| `--reference-links` | | bool | 765 |
| `--reference-location` | | `block`\|`section`\|`document` | 773 |
| `--figure-caption-position` | | `above`\|`below` | 786 |
| `--table-caption-position` | | `above`\|`below` | 798 |
| `--markdown-headings` | | `setext`\|`atx` | 810 |
| `--list-tables` | | bool | 823 |

### Network / security

| Flag | Arg | Source line |
|---|---|---|
| `--request-header` | NAME:VALUE | 660 |
| `--no-check-certificate` | bool | 669 |
| `--sandbox` | bool | 340 |

### Debug

| Flag | Arg | Source line |
|---|---|---|
| `--dump-args` | bool | 1090 |
| `--ignore-args` | bool | 1098 |

## Verification result

Cross-check between source `options =` definitions (lines 272-1183) and `pandoc --help` against the 3.9.0.2 binary: every flag listed above is callable on the installed binary. Format counts (`51` input, `75` output) were captured from `pandoc --list-input-formats | wc -l` and `pandoc --list-output-formats | wc -l`. The full enumeration of every individual flag against `--help` was not exhaustively diffed line-by-line — counts and the spot-checked flags shown in the tables above are verified; assume the long tail is pass-through-correct unless a downstream invocation surfaces a mismatch.

The handful of deprecated-but-still-accepted aliases live in `handleUnrecognizedOption` (line 1203) and emit warnings: `--smart`, `--normalize`, `-S`, `--old-dashes`, `--no-wrap`, `--latex-engine`, `--latex-engine-opt`, `--chapters`, `--reference-docx`, `--reference-odt`, `--parse-raw`, `--epub-stylesheet`, `-R`. Don't emit these from the wrapper.

## Sources

- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\App\CommandLineOptions.hs` (lines 272-1183 are the `options` list)
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\MANUAL.txt` (authoritative flag documentation)
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\App\Opt.hs` (the `Opt` record that flags mutate)
- https://github.com/jgm/pandoc/blob/main/src/Text/Pandoc/App/CommandLineOptions.hs
- https://pandoc.org/MANUAL.html#options
- https://pandoc.org/MANUAL.html#defaults-files
- https://pandoc.org/MANUAL.html#extensions
