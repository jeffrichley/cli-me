# pandoc Skill Wiki

Agent-native CLI wrapper for pandoc — universal document converter (markdown ↔
PDF, DOCX, HTML, EPUB, LaTeX) with citations, templates, and Lua filters.

**MVP scope:** convert, citations, templates, filters, info. See [v0.2 deferred
features](#v02-deferred-features) below for what's intentionally not yet wrapped.

## Source Analysis

- [Analyzed Version](source-analysis/analyzed-version.md) — pandoc 3.9.0.2, commit `c15e062`
- [API Surface](source-analysis/api-surface.md) — CLI flags, Lua API, template variables, defaults files
- [CLI Interface](source-analysis/cli-interface.md) — complete flag inventory grouped by purpose
- [Internal Architecture](source-analysis/internal-architecture.md) — readers → AST → writers + filter pipeline
- [Key Functions](source-analysis/key-functions.md) — source file:line references for the wrapper

## Techniques

- [Basic Conversion](techniques/basic-conversion.md) — md ↔ {pdf, docx, html, epub, latex} with `--standalone`, `--toc`, `--metadata`
- [Citations](techniques/citations.md) — `--citeproc`, `--bibliography`, `--csl` (BibTeX, BibLaTeX, CSL-JSON, CSL-YAML, RIS)
- [Templates](techniques/templates.md) — `--template` (text formats), `--reference-doc` (DOCX/ODT/PPTX), `--include-*`
- [Filters](techniques/filters.md) — Lua filters, JSON filters, pandoc-crossref, filter ordering
- [Metadata & Frontmatter](techniques/metadata-and-frontmatter.md) — YAML blocks, `--metadata`, `--metadata-file`, `--defaults`

## Operational

- [Log](log.md) — append-only build log
- [Gotchas](gotchas.md) — known footguns, version-dependent behavior, Windows-specific issues
- [Future Scope](future-scope.md) — v0.2 deferred features (slides, notebooks, custom writers, etc.)

## v0.2 Deferred Features

The MVP intentionally leaves the following for later releases. See
[future-scope.md](future-scope.md) for full detail.

- Slides (beamer, reveal.js, slidy, S5, DZSlides)
- Jupyter notebook formats (ipynb reader/writer)
- Exotic format pairs (MediaWiki, DokuWiki, Jira, Org-mode, AsciiDoc, RST, OPML, Textile, Muse, FB2)
- Custom Lua-based writers (`--writer=path/to/writer.lua`)
- Advanced filter patterns (panflute, JSON filter pipeline, multi-filter chaining)
- Deep template authoring (creating templates from scratch, partials, advanced syntax)
- Math rendering modes (`--mathjax`, `--katex`, `--webtex`, `--mathml`, `--gladtex`)
- Code highlighting customization (`--syntax-definition`, custom highlight styles)
- Extension-flag mastery (per-format extension defaults, GFM vs CommonMark trade-offs)
- pandoc-server (HTTP API mode — unlikely to be wrapped; not in scope)
