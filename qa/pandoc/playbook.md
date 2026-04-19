# pandoc Skill — QA Playbook

This is the contract that Phase 3 implementation agents and reviewers
read FIRST. It documents what every command must do, what its inputs
and outputs are, how to verify success, and what edge cases to test.

Five command groups (MVP):
- [info](#info-group) — version, formats, engines
- [convert](#convert-group) — md ↔ {pdf, docx, html, epub, latex}
- [citations](#citations-group) — bibliography rendering with citeproc
- [templates](#templates-group) — print, apply, eisvogel
- [filters](#filters-group) — apply, crossref-check

For each command:
- **Signature** — exact CLI shape
- **Behavior** — what pandoc invocation it builds
- **Verification** — how the test confirms success
- **Edge cases** — boundary conditions tests must cover
- **Error contract** — exit code + stderr message on failure

---

## info group

### `info version`

**Signature:** `pandoc-cli info version`

**Behavior:** Calls `pandoc --version`, prints just the parsed version
string (e.g. `3.9.0.2`) to stdout. Exit 0.

**Verification:** stdout matches `r"^\d+\.\d+(\.\d+)*$"`; exit 0.

**Edge cases:**
- pandoc not installed → exit 1, stderr starts with `ERROR: pandoc not found in PATH`.
- pandoc exits non-zero → exit non-zero, stderr surfaces the error.

**Error contract:** non-zero on missing pandoc; clear install instructions.

### `info formats`

**Signature:** `pandoc-cli info formats [--input | --output]`

**Behavior:** Without flags: prints two columns "INPUT" and "OUTPUT" listing
all formats. With `--input`: list input formats only. With `--output`: list
output formats only. Output to stdout, one format per line in the column.

**Verification:** count of input formats ≥ 50, output formats ≥ 70 (pandoc
3.9.0.2 reports 51/75); contains known formats `markdown`, `html`, `docx`, `latex`.

**Edge cases:**
- both flags passed → exit 1 with mutual-exclusion error.

### `info engines`

**Signature:** `pandoc-cli info engines`

**Behavior:** Probes each of the engines in `backend.PDF_ENGINES` against
PATH, prints two sections: "Available" (engines found) and "Not installed"
(the rest). Each line: `<engine>` for available, `<engine>  (not installed)`
for missing.

**Verification:** stdout contains a header for each section; at least one
engine listed in each section on this Windows + MiKTeX machine
(pdflatex, xelatex available; weasyprint depends).

**Edge cases:**
- No engines installed at all → "Available" section is empty but command
  still exits 0 (this is informational, not an error).

---

## convert group

### `convert to`

**Signature:**
```
pandoc-cli convert to INPUT OUTPUT
  [--from FORMAT] [--to FORMAT]
  [--standalone / --no-standalone]
  [--toc] [--toc-depth N]
  [--metadata KEY=VALUE]  (repeatable)
  [--pdf-engine ENGINE]
  [--embed-resources]
```

**Behavior:** Builds pandoc invocation with `INPUT -o OUTPUT` plus any
forwarded flags. Format detection is left to pandoc (extensions). For
PDF output, validates that a PDF engine is available (uses
`backend.find_pdf_engines()`); if `--pdf-engine` is omitted, pandoc picks
default.

**Verification by output format:**
- `.html` → `assert_html_doctype` (when `--standalone` is on or implicit)
- `.docx` → `assert_docx_magic` (PK header)
- `.pdf` → `assert_pdf_magic` (`%PDF-` header)
- `.epub` → `assert_epub_magic` (zip with `mimetype` near start)
- `.tex` (latex) → file is non-empty plain text, contains `\begin{document}` when standalone

**Edge cases:**
- INPUT does not exist → exit 1, stderr `ERROR: Input file not found: <path>`.
- OUTPUT directory does not exist → pandoc errors; surface that.
- PDF requested but no engine on PATH → exit 1, stderr lists engines pandoc
  found and suggests installation.
- `OUTPUT == "-"` for binary formats (PDF/DOCX) → pandoc emits the
  "Cannot write pdf output to terminal" error verbatim; surface it.
- `--from` / `--to` extension syntax (`markdown+yaml_metadata_block`) → must
  be passed through verbatim, not split.
- Spaces in INPUT/OUTPUT paths → Windows-safe quoting (subprocess.run with
  list args handles this automatically; tests should include a path-with-
  spaces case).

**Error contract:** any pandoc non-zero exit propagates with stderr surfaced.

---

## citations group

### `citations render`

**Signature:**
```
pandoc-cli citations render INPUT OUTPUT
  --bibliography BIB
  [--csl CSL]
  [--from FORMAT] [--to FORMAT]
  [--standalone / --no-standalone]
  [--metadata KEY=VALUE]  (repeatable)
```

**Behavior:** Builds pandoc invocation with `--citeproc --bibliography BIB`
and (if given) `--csl CSL`. Forwards other flags. Auto-adds `--standalone`
if output extension is binary (pdf/docx/epub).

**Verification:**
- Output file exists and matches the format magic per `convert to`.
- Output text contains the rendered citation: e.g. for `[@smith2020]` with
  the default Chicago style, the rendered text contains `(Smith 2020)` or
  `Smith (2020)`. (For HTML output, decode and search.)
- A "References" / "Works Cited" / "Bibliography" section appears in the
  output (or wherever `<div id="refs">` was placed).

**Edge cases:**
- `--bibliography` file not found → pandoc errors; surface.
- BibTeX file with bad syntax → pandoc errors; surface.
- Citation key in markdown that's not in .bib → pandoc emits
  `[WARNING] Citeproc: citation <key> not found` to stderr but exits 0.
  Test asserts the warning appears.
- `--csl` file not found → pandoc errors; surface.
- Combined with `--natbib` or `--biblatex` → reject before invoking
  pandoc; exit 1 with mutex error.

---

## templates group

### `templates print FORMAT`

**Signature:** `pandoc-cli templates print FORMAT`

**Behavior:** Calls `pandoc --print-default-template=FORMAT` and prints
result to stdout.

**Verification:**
- Exit 0; stdout is non-empty.
- For `latex`: contains `\documentclass`.
- For `html5`: contains `<!doctype html>` or `<html`.

**Edge cases:**
- Unknown format (e.g. `notarealformat`) → pandoc exits non-zero; surface.

### `templates apply`

**Signature:**
```
pandoc-cli templates apply INPUT OUTPUT --template TEMPLATE
  [--from FORMAT] [--to FORMAT]
  [--variable KEY=VALUE]  (repeatable)
  [--metadata KEY=VALUE]  (repeatable)
```

**Behavior:** Builds pandoc with `--template TEMPLATE`. Auto-enables
`--standalone` (pandoc does this implicitly when `--template` is set, but
log it for clarity). Forwards `--variable` and `--metadata`.

**Verification:**
- Output exists, format-appropriate magic.
- For LaTeX template using `$title$`: output text contains the title value
  passed via `--metadata title=...` or YAML frontmatter.

**Edge cases:**
- Template file not found → pandoc errors; surface.
- `--template` for a binary format pandoc doesn't accept it for (DOCX —
  pandoc would silently ignore for DOCX since DOCX uses --reference-doc) →
  warn the user that --template only applies to text-based formats.

### `templates eisvogel`

**Signature:**
```
pandoc-cli templates eisvogel INPUT OUTPUT
  [--toc]
  [--variable KEY=VALUE]  (repeatable)
  [--pdf-engine ENGINE]   (default: xelatex if available, else pdflatex)
```

**Behavior:** Forces PDF output. Resolves `bundled_template_path("eisvogel.latex")`
and passes `--template <path>`. Uses `xelatex` engine by default (Eisvogel
recommends it). Forwards optional flags.

**Verification:**
- OUTPUT has PDF magic.
- Skip cleanly if no LaTeX engine available.

**Edge cases:**
- Bundled template missing (someone deleted it) → exit 1 with clear error.
- OUTPUT not a `.pdf` extension → either coerce or warn (decision: warn but
  proceed; pandoc honors the explicit `-o` regardless).

---

## filters group

### `filters apply`

**Signature:**
```
pandoc-cli filters apply INPUT OUTPUT
  [--lua-filter PATH]      (repeatable)
  [--filter PATH]          (repeatable, JSON filter)
  [--from FORMAT] [--to FORMAT]
  [--standalone / --no-standalone]
```

**Behavior:** Forwards every `--lua-filter` and `--filter` to pandoc in CLI
order (preserves filter ordering — see filters.md gotcha). Validates that
each filter file exists before invoking pandoc.

**Verification:**
- For Lua uppercase-headings filter on `simple_md`: output (e.g. HTML)
  contains `<h1>HEADING ONE</h1>` (uppercased).
- Output exists with appropriate magic.

**Edge cases:**
- Filter file not found → exit 1 BEFORE invoking pandoc with clear error.
- Filter execution error (broken Lua) → pandoc errors; surface stderr.
- Empty filter list → just runs pandoc without filters.
- Mixing `--lua-filter` and `--filter` (Python JSON filter) — order matters;
  preserve as given.

### `filters crossref-check`

**Signature:** `pandoc-cli filters crossref-check`

**Behavior:** Looks for `pandoc-crossref` on PATH. If found: print path +
its `--version` output. If missing: print install instructions and exit 1.

**Verification:**
- When present: stdout contains the path AND a version line; exit 0.
- When missing: stderr contains "pandoc-crossref" and "install"; exit 1.

**Edge cases:**
- pandoc-crossref present but version mismatch with pandoc → just report
  the version, don't try to enforce compatibility. Document the matrix in
  the wiki. (Future: `--strict` flag could enforce.)

---

## Cross-cutting test discipline

- Every Tier 1 (`@pytest.mark.command_graph`) test mocks subprocess via
  `monkeypatch` or `unittest.mock.patch` on `pandoc_cli.backend.run_pandoc`
  (or the relevant helper) and asserts the **constructed argument list**.
- Every Tier 2 (`@pytest.mark.integration`) test invokes pandoc for real
  via the CLI (typer.testing.CliRunner) and uses verification helpers from
  `qa/pandoc/_pandoc_helpers.py` (import via `from _pandoc_helpers import assert_pdf_magic, ...`).
- "File exists and is non-empty" alone is insufficient — every Tier 2 test
  must assert at least one format-specific property (magic bytes, text
  content, count of structural elements).
- Tests that depend on a LaTeX engine, weasyprint, or pandoc-crossref MUST
  use the `latex_engine` / `html_pdf_engine` / `has_pandoc_crossref`
  fixtures and skip cleanly when unavailable.
- All paths in tests must use `tmp_path` — never write into the repo or
  the user's home directory.
