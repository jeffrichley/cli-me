# Templates

## When to Use

Use templates whenever the default pandoc output doesn't match what you need to ship. Three distinct mechanisms exist, and picking the wrong one wastes hours:

- **`--template FILE`** — replace the entire skeleton wrapping the document body. Text-based outputs only (LaTeX, HTML, Markdown, RTF). Use when you need full control over preamble, page geometry, fonts, headers, footers.
- **`--reference-doc FILE`** — point pandoc at a sample DOCX/ODT/PPTX whose styles will be copied into the output. Binary outputs only. Use for branded Word documents (47 Tabs decks, NIWC reports).
- **`--include-in-header / --include-before-body / --include-after-body`** — inject raw content at fixed locations without replacing the template. Use for one-off LaTeX preamble additions, custom CSS, page footers.

Combine with [metadata-and-frontmatter](metadata-and-frontmatter.md) to feed template variables. Combine with [basic-conversion](basic-conversion.md) for output formats and PDF engines.

## Technique

### `--template` for Text-Based Formats

Pandoc ships with a default template per text-based output format. The template is a text file with variable interpolation. Override the default with `--template my-template.tex` (or `.html`, etc.). The path can be:

- An absolute or relative path to a file
- A bare name (e.g., `eisvogel`) — pandoc looks in `${data-dir}/templates/` first, then includes the requested format extension automatically

To see the default template for any format and use it as a starting point:

```bash
pandoc --print-default-template=latex > my-template.tex
pandoc --print-default-template=html > my-template.html
pandoc --print-default-template=revealjs > slides.html
```

The default templates are also available in the pandoc source at https://github.com/jgm/pandoc/tree/main/data/templates.

### Pandoc Template Syntax

Templates use a small directive language:

| Syntax | Meaning |
|--------|---------|
| `$title$` | Insert the value of the `title` variable |
| `$if(toc)$ ... $endif$` | Conditional block (true if variable is set and not empty) |
| `$if(toc)$ A $else$ B $endif$` | Conditional with else branch |
| `$for(author)$ $author$ $sep$, $endfor$` | Loop over a list variable; `$sep$` between items |
| `$author.name$` | Access nested object field (when value is a YAML map) |
| `$body$` | Required — where the document body is inserted |
| `$$` | Literal dollar sign |

Variables come from three sources. `--variable key=value` (`-V`) writes into a separate template-only variable namespace and always wins for that namespace. `--metadata key=value` (`-M`) and YAML frontmatter both write into the document metadata namespace, which the template engine also consults — and the metadata priority order (highest wins) is: `-M` on the command line, then frontmatter in the document, then `--metadata-file` (see [metadata-and-frontmatter](metadata-and-frontmatter.md) for runtime-verified details). The difference between `-V` and `-M`: `-V` only affects the template; `-M` becomes part of the document's metadata block (visible to filters).

### `--reference-doc` for DOCX, ODT, PPTX

Pandoc generates DOCX by populating a Word template with content. The default reference is plain. Replace it with your branded one:

```bash
pandoc --print-default-data-file reference.docx > custom-reference.docx
```

Note: write to a *different* filename than `reference.docx`. Pandoc itself ships a file named `reference.docx` and resolves the bare name `reference.docx` against the data dir. Writing the dump to the same name in the current directory is harmless if `cwd` is not your data dir, but if you ever do this *inside* the data dir you will overwrite pandoc's own copy.

Open `custom-reference.docx` in Word. Modify the styles (Heading 1, Heading 2, Body Text, Title, Subtitle, Block Text, Caption, Source Code, etc.). Save. Then:

```bash
pandoc draft.md --reference-doc custom-reference.docx -o draft.docx
```

The output uses your styles. Pandoc replaces only the body content; your headers, footers, page numbers, page setup, and style definitions carry over.

Styles pandoc maps content to (canonical names from the MANUAL `--reference-doc` section and the bundled `reference.docx`; names are case- and space-sensitive):

| Pandoc element | Word style |
|----------------|-----------|
| `# Heading` | Heading 1 |
| `## Heading` | Heading 2 |
| ... up to `Heading 9` | Heading 3 / 4 / 5 / 6 / 7 / 8 / 9 |
| First body paragraph | First Paragraph |
| Subsequent body paragraphs | Body Text |
| Compact paragraph (in tight lists) | Compact |
| `> Blockquote` | Block Text |
| Blockquote inside a footnote | Footnote Block Text |
| Code block | Source Code (created on the fly if absent from the reference) |
| Inline code | Verbatim Char |
| Image caption | Image Caption |
| Table caption | Table Caption |
| Generic caption | Caption |
| Figure (caption + image group) | Captioned Figure / Figure |
| Title (from frontmatter) | Title |
| Subtitle | Subtitle |
| Author | Author |
| Date | Date |
| Abstract body / heading | Abstract / AbstractTitle |
| Bibliography entries | Bibliography |
| Definition list term / body | Definition Term / Definition |
| Footnote text | Footnote Text |
| Footnote reference (superscript) | Footnote Reference |
| Hyperlink | Hyperlink |
| Section number (for numbered headings) | Section Number |
| TOC heading | TOC Heading |
| Tables | Table (table style) |

For ODT use `--print-default-data-file reference.odt`. For PPTX use `reference.pptx`. The same flag handles all three.

### `--include-*` Injection Flags

Three flags inject raw content into a text-based output without replacing the template:

| Flag | Where it lands (LaTeX) | Where it lands (HTML) |
|------|------------------------|------------------------|
| `--include-in-header FILE` | Before `\begin{document}` | Inside `<head>` |
| `--include-before-body FILE` | After `\begin{document}`, before content | After `<body>`, before content |
| `--include-after-body FILE` | After content, before `\end{document}` | After content, before `</body>` |

All three are repeatable. Content is inserted verbatim — pandoc does not parse it.

### Data Directory and Template Search Order

Pandoc looks for templates in this order:

1. The path you passed (if it has a `/` or `\`)
2. `${PANDOC_DATA_DIR}/templates/` (set via `--data-dir DIR` or env var `XDG_DATA_HOME`)
3. The default user data dir: `~/.local/share/pandoc/templates/` on Unix, `%APPDATA%\pandoc\templates\` on Windows
4. The bundled defaults baked into the binary

Find your data dir:

```bash
pandoc --version
# Look for "User data directory: ..."
```

Drop reusable templates and `.csl` files there to avoid passing absolute paths every invocation.

## CLI Commands

**Print and save the default LaTeX template for editing:**
```bash
pandoc --print-default-template=latex > 47tabs-template.tex
```
Verify: file starts with `\documentclass{...}` and contains `$body$` somewhere in the middle.

**Print and save the default DOCX reference:**
```bash
pandoc --print-default-data-file reference.docx > 47tabs-reference.docx
```
Verify: open in Word; you see a multi-page sample doc with all the named styles applied.

**DOCX with a branded reference for 47 Tabs sales materials:**
```bash
pandoc onepager.md \
  --reference-doc 47tabs-reference.docx \
  --metadata title="47 Tabs - Enterprise Brief" \
  -o "47Tabs-Enterprise-Brief.docx"
```
Verify: DOCX opens with the title styled in the brand's Title style; `# Heading` lines use the brand's Heading 1 (font, color, spacing).

**Custom LaTeX template for a NIWC document with header/footer/page numbers:**

Save as `niwc-header.tex`:
```latex
\usepackage{fancyhdr}
\usepackage{lastpage}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small Distribution Statement A: Approved for Public Release}
\fancyhead[R]{\small NIWC PAC TR-2026-\jobname}
\fancyfoot[C]{\small \thepage\ of \pageref{LastPage}}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.4pt}
```

```bash
pandoc niwc-report.md \
  --pdf-engine=xelatex \
  --include-in-header niwc-header.tex \
  -V geometry:margin=1in \
  -V mainfont="Times New Roman" \
  -o NIWC-PAC-TR-2026-042.pdf
```
Verify: PDF every page shows the distribution statement top-left, document number top-right, and `Page 1 of N` centered at the bottom.

**Use a downloaded community template (e.g., Eisvogel for branded PDFs):**
```bash
# Drop eisvogel.latex into your data dir
pandoc --version  # find user data directory
# Copy eisvogel.latex into ${data-dir}/templates/

pandoc pitch.md \
  --pdf-engine=xelatex \
  --template eisvogel \
  -V titlepage=true \
  -V titlepage-color="0F4C81" \
  -V titlepage-text-color="FFFFFF" \
  -o "47Tabs-Pitch.pdf"
```
Verify: PDF opens with a colored title page and Eisvogel's signature header style.

**Custom HTML template for a self-hosted onepager:**

Save as `47tabs.html`:
```html
<!DOCTYPE html>
<html lang="$lang$">
<head>
  <meta charset="UTF-8">
  <title>$title$</title>
  <link rel="stylesheet" href="https://cdn.47tabs.com/brand.css">
  $for(header-includes)$$header-includes$$endfor$
</head>
<body>
  <header><img src="https://cdn.47tabs.com/logo.svg" alt="47 Tabs"></header>
  <main>
  $if(title)$<h1>$title$</h1>$endif$
  $if(subtitle)$<p class="subtitle">$subtitle$</p>$endif$
  $body$
  </main>
  <footer>&copy; 2026 47 Tabs Inc.</footer>
</body>
</html>
```

```bash
pandoc onepager.md \
  --template 47tabs.html \
  --metadata title="Enterprise Tier" \
  --metadata subtitle="Q2 2026" \
  -o onepager.html
```
Verify: HTML output uses your custom skeleton, brand CSS link is in `<head>`, logo in `<header>`.

**Inject a print-only stylesheet for HTML output:**

Save as `print.css`:
```html
<style media="print">
  @page { margin: 0.75in; }
  a { color: black; text-decoration: none; }
  pre { page-break-inside: avoid; }
</style>
```

```bash
pandoc article.md -s --include-in-header print.css -o article.html
```
Verify: viewing source, the `<style>` block appears inside `<head>`.

## Under the Hood

Pandoc templates are processed by the **DocTemplates** library (https://github.com/jgm/doctemplates). It is a small, pandoc-specific template engine — not Jinja, not Mustache, not Liquid. Variables resolve against the document's metadata map plus any `-V`/`--variable` overrides.

For text-based formats, the writer assembles the document by:

1. Generating the body content from the AST.
2. Setting variables based on document metadata (title, author, date, abstract, toc, etc.).
3. Running the template with those variables and `$body$` set to the generated body.
4. Writing the resulting string to the output file.

For DOCX/ODT/PPTX, pandoc opens the reference document as a ZIP archive (these are all OOXML/ODF, which are ZIP containers of XML). It extracts the styles and document properties, swaps in newly generated content XML, and re-zips. This is why custom styles transfer cleanly: pandoc only modifies the content XML, not the styles XML.

`--include-in-header` and friends bypass the template machinery entirely — they pass through to a metadata variable (`header-includes`, `include-before`, `include-after`) that the default template knows how to splice in. If you write a custom template, remember to include `$for(header-includes)$$header-includes$$endfor$` in the right place or these flags become silently no-ops.

## Common Gotchas

- **`--reference-doc` only works for docx/odt/pptx.** Pandoc accepts the flag for any output format — including PDF, HTML, LaTeX, and Markdown — but only the docx, odt, and pptx writers consume it. For every other writer the flag is silently ignored: no warning, no error, exit code 0. The symptom is "my styling didn't apply" and there is nothing in the log to point you at the cause. Verified at runtime: `pandoc t.md --reference-doc=ref.docx -t html -o out.html` exits 0 with no diagnostic and no styling change.
- **`--template` only works for text-based formats.** It's silently ignored for DOCX/PPTX/EPUB. Use `--reference-doc` for those.
- **Style names are case-sensitive.** Word style "Heading1" (no space) does not equal "Heading 1" (with space). Pandoc maps to "Heading 1" exactly. Rename in Word to match.
- **Custom styles need to exist in the reference doc.** A markdown `:::{custom-style="Sidebar"}` block won't render styled unless your reference DOCX defines a paragraph style named `Sidebar`.
- **Pandoc-syntax templates predate every other template language.** Don't mix `{{ }}`, `{% %}`, or `<% %>` syntax — none of those work. Only `$...$`.
- **Forgetting `$body$`.** The most common custom-template bug. Without it, you get a beautifully styled empty document.
- **`--include-in-header` files are inserted verbatim.** No markdown parsing. If you put markdown in there, it lands as literal markdown in your output.
- **`-V` vs `--metadata` for booleans.** `-V toc` sets the variable to a true-ish value; `-V toc=false` sets it to the string `"false"`, which is truthy in doctemplates' `$if(toc)$ ... $endif$` (verified at runtime: `-V toc=false` fires the *YES* branch). To actually disable a template conditional, use `--metadata toc=false` (which fires the *NO* branch) or simply omit the flag entirely.
- **MiKTeX missing styles.** A custom LaTeX template that uses `\usepackage{fancyhdr}` etc. requires those packages. MiKTeX auto-installs on first use; if blocked, install via `mpm` or the MiKTeX Console.
- **Word file locked.** On Windows, if `Output.docx` is open in Word, pandoc fails with `permission denied`. Close Word first.

## Sources

- Pandoc User's Guide — Templates section: https://pandoc.org/MANUAL.html#templates
- Pandoc default templates in source: https://github.com/jgm/pandoc/tree/main/data/templates
- DocTemplates engine source: https://github.com/jgm/doctemplates
- Eisvogel community template (popular branded PDF template): https://github.com/Wandmalfarbe/pandoc-latex-template
- Pandoc User's Guide — Reference Docx: https://pandoc.org/MANUAL.html#option--reference-doc
- Pandoc data files (the bundled reference.docx etc.): https://github.com/jgm/pandoc/tree/main/data

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
