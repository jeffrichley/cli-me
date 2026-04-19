# Basic Conversion

## When to Use

Use this technique for any one-off document conversion: markdown to PDF for a 47 Tabs investor brief, markdown to DOCX for a NIWC deliverable, HTML to EPUB for distribution, or LaTeX to markdown when porting old academic content. This is the foundation every other technique builds on.

If you need bibliographic citations, see [citations](citations.md). If you need branded styling, see [templates](templates.md). If you need cross-references for figures and equations, see [filters](filters.md). If you need to share preset configurations across documents, see [metadata-and-frontmatter](metadata-and-frontmatter.md).

## Technique

### Format Auto-Detection

Pandoc infers input and output formats from file extensions. `pandoc draft.md -o draft.pdf` reads markdown and writes PDF without explicit format flags. The mapping is fixed in pandoc's source — `.md`/`.markdown` → markdown, `.docx` → docx, `.tex` → latex, `.html`/`.htm` → html, `.epub` → epub. When the extension is ambiguous or missing, pandoc errors out.

Override detection with `--from FORMAT` (`-f`) and `--to FORMAT` (`-t`). The format string accepts extension modifiers: `markdown+smart-citations` enables the `smart` extension and disables `citations`. The `+` and `-` prefixes are pandoc's extension toggle syntax — see `pandoc --list-extensions=markdown` for what each flavor supports.

### Standalone Output

By default, pandoc emits a fragment (just the body, no `<html>` wrapper, no LaTeX preamble). Pass `--standalone` (`-s`) to produce a complete, valid document with the format's full skeleton — DOCTYPE for HTML, `\documentclass` for LaTeX, container.xml for EPUB. PDF, DOCX, EPUB, and ODT are always standalone; the flag only matters for text-based outputs (HTML, LaTeX, RTF, etc.).

### Table of Contents

`--toc` (or `--table-of-contents`) inserts a TOC at the top of the document. `--toc-depth=N` (default 3) controls how many heading levels to include. The TOC respects `--number-sections` if both are set.

### Output Destination

`-o output.ext` writes to a file (and triggers extension-based format detection). Without `-o`, pandoc writes to stdout — useful for piping into other tools or quick previews:

```bash
pandoc README.md -t plain | less
```

PDF and DOCX cannot go to a terminal because they are binary formats. If you forget `-o`, pandoc errors with the exact message:

```
Cannot write pdf output to terminal.
Specify an output file using the -o option, or use '-o -' to force output to stdout.
```

Use `-o -` if you actually want the binary bytes on stdout (e.g. piping into another tool).

### PDF Engines

Pandoc does not write PDF directly. It generates an intermediate format (LaTeX by default) and shells out to a PDF engine. Pick the engine with `--pdf-engine=ENGINE`.

| Engine | Intermediate | Notes |
|--------|--------------|-------|
| `pdflatex` | LaTeX | Fast, mature, ASCII-friendly. Limited Unicode and font support. |
| `xelatex` | LaTeX | Recommended default. Native Unicode, system font access via `mainfont:`. |
| `lualatex` | LaTeX | Like xelatex with Lua scripting in the document. Slower startup. |
| `tectonic` | LaTeX | Self-contained; downloads packages on demand. No system TeX install needed. |
| `wkhtmltopdf` | HTML | Renders via Webkit. Old, deprecated by upstream, but produces small PDFs. |
| `weasyprint` | HTML | Modern HTML/CSS-to-PDF. Good for design-driven layouts. Python install. |
| `prince` | HTML | Commercial. Excellent CSS Paged Media support. |
| `context` | ConTeXt | For ConTeXt users. |

These are the engines pandoc knows how to drive; each must be installed separately and on `PATH`. Pandoc validates the engine at runtime — if the chosen engine isn't found, pandoc errors with the message `Argument of --pdf-engine must be one of` followed by a list of the engines it actually located on `PATH` (e.g. just `weasyprint` and `wkhtmltopdf` on a machine with no TeX install). On this Windows machine MiKTeX is installed, so `pdflatex` and `xelatex` are both on PATH and either works out of the box. Pick `xelatex` for anything with non-ASCII characters or custom fonts.

### Resource Handling

When converting markdown that references images or include files, pandoc resolves relative paths from the markdown file's directory. Override with `--resource-path=DIR1:DIR2` (use `;` as separator on Windows). Multiple directories search in order.

`--extract-media=DIR` pulls embedded media (data: URIs in HTML, image bytes in DOCX/EPUB) out into a directory of files. Useful for pulling assets out of a Word doc.

For HTML output, `--embed-resources --standalone` produces a single self-contained `.html` file with all images, CSS, and fonts inlined as data: URIs. This replaces the deprecated `--self-contained` flag (still works, but emits a warning since pandoc 2.19).

## CLI Commands

**Markdown to PDF (default xelatex with MiKTeX):**
```bash
pandoc draft.md -o draft.pdf --pdf-engine=xelatex
```
Verify success: `draft.pdf` exists and opens in any PDF viewer. If you see `! LaTeX Error: File 'xyz.sty' not found`, MiKTeX should auto-install on first use; if it doesn't, run `mpm --install=xyz` from the MiKTeX shell.

**Markdown to DOCX:**
```bash
pandoc draft.md -o draft.docx
```
Verify: `draft.docx` opens in Word. Headings map to Word's `Heading 1`/`Heading 2` styles automatically.

**Markdown to standalone HTML with TOC:**
```bash
pandoc draft.md -s --toc --toc-depth=2 -o draft.html
```
Verify: open in browser; you should see a TOC at the top with anchor links to each `##` and `###` heading.

**Markdown to EPUB:**
```bash
pandoc book.md -o book.epub --metadata title="My Book" --metadata author="Jeff Richley"
```
Verify: `book.epub` opens in Calibre, Apple Books, or any EPUB reader. Metadata appears as the book title and author.

**Markdown to LaTeX (no PDF, just the .tex source):**
```bash
pandoc draft.md -s -o draft.tex
```
Verify: `draft.tex` starts with `\documentclass{article}` and ends with `\end{document}`.

**HTML to markdown (reverse direction):**
```bash
pandoc page.html -t markdown -o page.md
```
Verify: `page.md` contains markdown headings (`#`), bold (`**...**`), and links (`[text](url)`).

**DOCX to markdown (extract text from a Word doc):**
```bash
pandoc report.docx -t markdown --extract-media=./media -o report.md
```
Verify: `report.md` contains the document text; `./media/` contains any embedded images (named `image1.png`, `image2.png`, etc.).

**Self-contained single-file HTML (everything inlined):**
```bash
pandoc article.md -s --embed-resources -o article.html
```
Verify: `article.html` is one large file with no external `<img src>` references — all images are `data:image/png;base64,...`.

**Explicit format with extensions:**
```bash
pandoc README.md -f markdown+smart+definition_lists -t html5 -o README.html
```
Verify: smart quotes (`"foo"` → `"foo"`) and definition list syntax both render.

**Full md→PDF for a 47 Tabs investor brief:**
```bash
pandoc pitch.md \
  -o "47Tabs-Pitch-Q2.pdf" \
  --pdf-engine=xelatex \
  --standalone \
  --toc --toc-depth=2 \
  --metadata title="47 Tabs — Q2 Investor Brief" \
  --metadata author="Jeff Richley" \
  --metadata date="April 2026" \
  -V geometry:margin=1in \
  -V mainfont="Inter" \
  -V linkcolor:blue
```
Verify: PDF opens, title page shows the metadata, TOC lists `##` headings, body text renders in Inter (or a fallback if Inter is not installed).

## Under the Hood

Pandoc is built around an internal AST (abstract syntax tree). Every conversion follows the pipeline `reader → AST → writer`. The reader parses the input format into pandoc's `Pandoc` data structure (a tree of `Block` and `Inline` nodes); the writer serializes that tree to the output format. Filters ([filters](filters.md)) hook into the gap between reader and writer to manipulate the AST.

For PDF specifically, there is no PDF writer. Instead, pandoc invokes the matching text writer (LaTeX for `xelatex`/`pdflatex`/`lualatex`/`tectonic`, HTML for `wkhtmltopdf`/`weasyprint`/`prince`, ConTeXt for `context`) and pipes the output to the engine. If the engine is missing or fails, you get the engine's stderr verbatim — often cryptic. The fix is almost always "install the engine" or "the engine choked on a package; install the package."

`--standalone` controls whether the writer wraps its output in the format's default template. The template is a text file with variable substitution (see [templates](templates.md)). Without `--standalone`, you get the body fragment only.

## Common Gotchas

- **Spaces in paths.** Quote them: `pandoc "My Doc.md" -o "My Doc.pdf"`. Unquoted paths split on whitespace and pandoc treats each fragment as a separate input file.
- **Windows path separators.** Pandoc accepts forward slashes everywhere on Windows: `pandoc C:/docs/in.md -o C:/docs/out.pdf`. Backslashes work too but require escaping in shell scripts.
- **Missing PDF engine = cryptic error.** `pandoc: xelatex not found. xelatex is needed for pdf output.` Install MiKTeX or TeX Live, or pick a different engine with `--pdf-engine=`.
- **Word has the file open.** On Windows, if `draft.docx` is open in Word, pandoc fails with `permission denied`. Close the file first.
- **Binary format to terminal.** `pandoc draft.md -t pdf` (no `-o`) errors with the exact message: `Cannot write pdf output to terminal. Specify an output file using the -o option, or use '-o -' to force output to stdout.` Use `-o file.pdf` for normal use, or `-o -` if you really want the bytes on stdout (e.g. piping into another tool).
- **`--self-contained` deprecated.** Use `--embed-resources --standalone` instead. The old flag still works but warns.
- **MiKTeX first-use install prompt.** First-time package installs may prompt for confirmation in a popup. Configure auto-install in MiKTeX Console → Settings → "Always install missing packages on the fly."

## Sources

- Pandoc User's Guide (the canonical reference): https://pandoc.org/MANUAL.html
- Pandoc demos page (39 example invocations): https://pandoc.org/demos.html
- pandoc on GitHub (releases, source): https://github.com/jgm/pandoc
- MiKTeX (Windows TeX distribution): https://miktex.org/
- WeasyPrint (HTML/CSS PDF engine): https://weasyprint.org/
- Tectonic (self-contained TeX engine): https://tectonic-typesetting.github.io/

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
