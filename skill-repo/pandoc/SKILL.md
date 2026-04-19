---
name: pandoc
description: Universal document conversion CLI for pandoc — convert markdown to PDF, DOCX, HTML, EPUB, LaTeX with citations, templates, and Lua filters. Use when asked to "convert to pdf", "render markdown", "build docx", "compile thesis", "make epub", "render report", "generate document", "format my paper", "compile to docx", "build a pdf", "apply citations", "use bibtex", "convert markdown to pdf without latex" (uses weasyprint), or to produce a formatted document from markdown. Slides (beamer/reveal.js) and Jupyter notebooks are NOT yet supported — deferred to v0.2.
---

> **Status (v0.1 scaffold):** Phase 2 scaffolding is in place; command bodies
> arrive in Phase 3. The CLI loads and lists subcommands but invocations like
> `pandoc-cli convert to ...` will return "No such command" until Phase 3
> ships. Remove this banner when Phase 3 lands.

# pandoc — cli-me skill

CLI-powered interface for pandoc. This skill wraps the real `pandoc` executable
— it does not reimplement document conversion in Python. Pandoc is invoked via
subprocess.

## Prerequisites

- pandoc must be installed: `winget install JohnMacFarlane.Pandoc` (Windows) /
  `brew install pandoc` (macOS) / `apt install pandoc` (Linux). Verify with
  `pandoc --version`.
- For PDF output: a LaTeX engine on PATH. Recommended: `xelatex` or `pdflatex`
  via MiKTeX (Windows) / TeX Live (macOS/Linux), OR `weasyprint` (HTML→PDF
  path, no LaTeX). Engine availability is detected at runtime; missing engines
  produce a clear error listing what was found.
- For citation cross-references: optional `pandoc-crossref` filter. Install
  via `cabal install pandoc-crossref` or download a binary from
  https://github.com/lierdakil/pandoc-crossref/releases (must match your
  pandoc version). The skill verifies presence and emits an install hint
  when missing — it does not auto-install.
- Python 3.12+

## CLI Commands

Run commands from the skill's `scripts/` directory so each skill uses its
own isolated venv:

```bash
cd skill-repo/pandoc/scripts
uv run pandoc_cli.py <group> <command> [options]
```

Bundled Eisvogel template path (used implicitly by `templates eisvogel` but
also useful for direct pandoc invocations): `scripts/templates/eisvogel.latex`.

### Available Commands (MVP scope)

**convert** — Format conversion (md ↔ {pdf, docx, html, epub, latex})
- `convert to INPUT OUTPUT` — convert between formats; auto-detects from extensions

**citations** — Bibliography and citation rendering
- `citations render INPUT OUTPUT --bibliography refs.bib [--csl style.csl]` — render with citations

**templates** — Custom output styling
- `templates print FORMAT` — print pandoc's default template for a format
- `templates apply INPUT OUTPUT --template t.tex` — convert with a custom template
- `templates eisvogel INPUT OUTPUT [--toc]` — convert to PDF using the bundled Eisvogel LaTeX template

**filters** — Lua and JSON filter pipelines
- `filters apply INPUT OUTPUT --lua-filter f.lua [...]` — apply one or more filters
- `filters crossref-check` — verify pandoc-crossref is installed and version-compatible

**info** — Introspection
- `info version` — show installed pandoc version
- `info formats` — list input/output formats
- `info engines` — list PDF engines available on PATH

### Deferred to v0.2

Slides (beamer/reveal.js), Jupyter notebooks, exotic format pairs (MediaWiki,
Org, AsciiDoc, RST, etc.), custom Lua writers, advanced filter patterns, deep
template authoring, math rendering modes, code highlighting customization,
extension-flag mastery. See `references/future-scope.md`.

## Default Behavior

- **Output location:** `OUTPUT` argument is required for `convert` and
  `citations render` (pandoc cannot write binary formats like PDF/DOCX to
  stdout). For text formats, pass `-` as OUTPUT to write to stdout.
- **Format auto-detection:** pandoc detects input/output format from file
  extensions (`.md` → markdown, `.docx` → docx, etc.). Use `--from`/`--to` to
  override.
- **`--standalone`:** auto-enabled for PDF/DOCX/EPUB outputs. Pandoc adds it
  implicitly when `--template` or `--include-*` flags are present.
- **PDF engine:** auto-selects `pdflatex` for `-t pdf` if available, else
  `weasyprint` for HTML→PDF flows. Pass `--pdf-engine` to override.
- **Filter ordering:** preserved as given on the command line. `--citeproc`
  should typically come last (after content-modifying filters).
- **Interactive prompts:** none. Pandoc never blocks waiting for input —
  except it WILL read stdin if no input file is given. The wrapper validates
  input file presence to avoid silent hangs.
- **Processing time:** sub-second for typical markdown documents. Multi-second
  for PDF (LaTeX compilation). Large files (>1000 pages) may take 30+ seconds
  for PDF. Use `timeout: 60000` for normal Bash invocations; `timeout: 300000`
  for large PDFs or filter pipelines.

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how something works under the hood, check
`references/source-analysis/`. For known footguns, check `references/gotchas.md`.
For features not yet wrapped, check `references/future-scope.md`.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Log what you did: `clime log append --skill pandoc --message "<what you did and learned>" --log-file references/log.md`
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
