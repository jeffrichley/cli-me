# Citations

## When to Use

Use this technique whenever a document needs formatted bibliographic citations and a reference list — PhD chapters, NIWC technical reports with cited prior work, white papers backing up claims with sources. Pandoc's citation engine handles in-text citations, reference list rendering, and switching between styles (APA, Chicago, IEEE, etc.) from the same source markdown.

If you only need plain hyperlinks without formal citations, skip this and use markdown links. If you need cross-references to figures and equations within the document, see [filters](filters.md) for `pandoc-crossref`.

## Technique

### The citeproc Story

Before pandoc 2.11 you needed an external `pandoc-citeproc` binary and a `--filter pandoc-citeproc` flag. Since 2.11 (October 2020), citation processing is built into pandoc itself. Activate it with `--citeproc`. The old `pandoc-citeproc` is deprecated and missing from current pandoc releases.

`--citeproc` reads citation references from your markdown, looks them up in your bibliography file, formats them according to a CSL style, and inserts the rendered text plus a reference list.

### Bibliography Files

Point pandoc at one or more bibliography sources with `--bibliography FILE` (repeatable). Pandoc detects the format from the extension:

| Extension | Format | Source |
|-----------|--------|--------|
| `.bib` | BibLaTeX (default for `.bib`) | Most common; LaTeX-native |
| `.bibtex` | BibTeX | Force BibTeX interpretation (vs `.bib` → BibLaTeX) |
| `.json` | CSL JSON | Native CSL format; Zotero export |
| `.yaml` | CSL YAML | Same data as CSL JSON, YAML-encoded |
| `.ris` | RIS | Reference manager exchange format |

This list is canonical: it matches the bibliography-format table in pandoc's MANUAL. EndNote XML is *not* a `--bibliography` format — pandoc does support EndNote XML as an *input document* format (`pandoc --from endnotexml ...`), but `--bibliography file.xml` errors with `Could not determine bibliography format for file.xml`. The legacy `.enl` extension (binary EndNote library) is also unsupported by pandoc.

You can also embed citations inline in the document's YAML frontmatter under the `references:` key — see [metadata-and-frontmatter](metadata-and-frontmatter.md).

### Citation Syntax

Pandoc citations live in square brackets and start with `@`:

| Markdown | Renders as (author-date) |
|----------|--------------------------|
| `[@smith2020]` | `(Smith 2020)` |
| `[@smith2020, p. 33]` | `(Smith 2020, p. 33)` |
| `[@smith2020, pp. 33-40]` | `(Smith 2020, pp. 33-40)` |
| `[-@smith2020]` | `(2020)` (suppress author) |
| `[@smith2020; @jones2019]` | `(Smith 2020; Jones 2019)` |
| `@smith2020 [p. 33]` | `Smith (2020, p. 33)` (in-text) |
| `[see @smith2020, chap. 1]` | `(see Smith 2020, chap. 1)` |
| `[@smith2020 {prefix} suffix]` | Custom prefix/suffix |

The citation key (`smith2020`, etc.) is whatever you set as the entry's identifier in the bibliography. BibTeX entries use the first token after `@article{`; CSL JSON uses the `id` field.

### Citation Style Language (CSL)

CSL is an XML format describing how citations and reference lists should look. Pandoc ships with `chicago-author-date` as the default. Pick a different style with `--csl style.csl`.

The Citation Style Language project maintains 10,000+ styles in their public repo: https://github.com/citation-style-language/styles. Browse by name (e.g., `apa.csl`, `ieee.csl`, `nature.csl`, `mla-9th-edition.csl`, `modern-language-association.csl`) or use the searchable Zotero Style Repository at https://www.zotero.org/styles.

Common styles for academic and technical writing:

| Style | File | Use |
|-------|------|-----|
| APA 7 | `apa.csl` | Psychology, social sciences, education |
| Chicago Author-Date | `chicago-author-date.csl` | Humanities, social sciences (default) |
| Chicago Notes-Bibliography | `chicago-note-bibliography.csl` | History, art (footnote-style) |
| IEEE | `ieee.csl` | Engineering, computer science (numeric `[1]`, `[2]`) |
| Nature | `nature.csl` | Natural sciences (superscript numbers) |
| MLA 9 | `modern-language-association.csl` | Literature, languages |
| Vancouver | `vancouver.csl` | Medicine, biomedical |
| ACM | `association-for-computing-machinery.csl` | Computer science (ACM venues) |

### Rendering Modes

Three ways to handle citations when targeting LaTeX/PDF:

1. **`--citeproc`** — pandoc renders citations to plain text in the AST. Output is identical across formats. Recommended default. Works for any format.
2. **`--natbib`** — pandoc emits `\citep{key}`/`\citet{key}` LaTeX commands. The PDF engine runs `bibtex` (via natbib package) to render. LaTeX-only.
3. **`--biblatex`** — pandoc emits `\autocite{key}` LaTeX commands. The PDF engine runs `biber` to render. LaTeX-only, more flexible than natbib.

Pick `--citeproc` unless you have a LaTeX template that requires natbib/biblatex, or your committee insists on a specific BibLaTeX style.

Note on combining these flags: pandoc 3.9.0.2 does **not** error or warn if you pass more than one of `--citeproc`, `--natbib`, `--biblatex` together — it accepts the combination silently and the last one specified wins for `cite-method`, but the result can be unpredictable (e.g. citeproc rendering combined with raw LaTeX `\cite` commands). Treat them as mutually exclusive in practice even though the binary doesn't enforce it.

### Reference List Placement

By default, pandoc appends the reference list to the end of the document under an auto-generated heading "References" (text varies by CSL style and `lang:` metadata).

To control placement, insert a div with `id="refs"` where you want the list:

```markdown
## Bibliography

::: {#refs}
:::
```

Anything between `:::` markers is replaced with the reference list. The heading stays where you wrote it.

To suppress the auto-heading, set `--metadata reference-section-title=""` or use `suppress-bibliography: true` in YAML.

## CLI Commands

**Minimum-viable cited document (markdown to PDF, default Chicago):**
```bash
pandoc chapter.md \
  --citeproc \
  --bibliography refs.bib \
  -o chapter.pdf
```
Verify: PDF contains `(Author Year)` in-text citations and a "References" section at the end with full entries.

**APA 7 style:**
```bash
pandoc chapter.md \
  --citeproc \
  --bibliography refs.bib \
  --csl apa.csl \
  -o chapter.pdf
```
Verify: in-text citations show as `(Smith, 2020)` (with comma); reference list uses APA's hanging indent format.

**IEEE numeric citations (engineering reports):**
```bash
pandoc whitepaper.md \
  --citeproc \
  --bibliography refs.bib \
  --csl ieee.csl \
  -o whitepaper.pdf
```
Verify: in-text citations appear as `[1]`, `[2]`; reference list is numbered and ordered by first appearance.

**Multiple bibliographies merged:**
```bash
pandoc thesis.md \
  --citeproc \
  --bibliography primary-sources.bib \
  --bibliography secondary-sources.bib \
  --bibliography web-archive.json \
  --csl apa.csl \
  -o thesis.pdf
```
Verify: citations resolve from any of the three files; pandoc errors loudly if a key appears in zero of them (`[WARNING] Citation foo2020 not found`).

**LaTeX with biblatex (PhD draft using a custom .cls):**
```bash
pandoc thesis.md \
  --biblatex \
  --bibliography refs.bib \
  -s \
  -o thesis.tex
```
Then compile with `latexmk -xelatex thesis.tex` (latexmk runs biber and xelatex enough times to resolve refs).
Verify: `thesis.tex` contains `\autocite{key}` calls and a `\printbibliography` near the end.

**Cited DOCX for a NIWC report:**
```bash
pandoc report.md \
  --citeproc \
  --bibliography refs.bib \
  --csl ieee.csl \
  --reference-doc niwc-template.docx \
  -o NIWC-Report-2026-04.docx
```
Verify: DOCX opens in Word with IEEE numeric citations; references appear under a styled heading matching the reference template.

**Equivalent via YAML frontmatter (preferred for project consistency):**
```yaml
---
title: "Bayesian Methods in HRI"
author: Jeff Richley
bibliography: refs.bib
csl: apa.csl
---

The state-of-the-art [@andrist2014] suggests that...
```

```bash
pandoc chapter.md --citeproc -o chapter.pdf
```
Verify: same output as passing `--bibliography` and `--csl` on the command line. CLI `--metadata` (`-M`) overrides frontmatter; frontmatter overrides `--metadata-file` (see [metadata-and-frontmatter](metadata-and-frontmatter.md) for the full priority order).

**Custom reference list location:**
```markdown
# Introduction

Recent work [@smith2020] has shown...

# Conclusion

...

# References

::: {#refs}
:::

# Appendix A
```

The bibliography renders inside the `#refs` div, with the appendix appearing after.

## Under the Hood

Pandoc's `--citeproc` runs as an internal filter between reader and writer. After parsing, the filter walks the AST looking for `Cite` nodes (created from `[@key]` syntax). For each `Cite`, it looks up the key in the bibliography, formats the citation per the CSL rules, and replaces the `Cite` node with the formatted inline text.

CSL is a sequence of declarative rendering rules — "for an article, output author last name, year in parens, italicized title, journal, volume, page range." The implementation is a pure Haskell port of the citeproc-js algorithm in pandoc's `citeproc` library. Disambiguation (when two cites share an author and year, append `a`, `b`, ...) is handled in a second pass.

The reference list is generated at the end by walking the collected citations and emitting one entry per unique key, sorted per the CSL style (alphabetical, citation order, etc.).

`--natbib` and `--biblatex` skip all of this and emit raw LaTeX commands. The PDF engine's bibliography processor (bibtex/biber) does the rendering. This is faster for huge bibliographies and gives you access to LaTeX-specific features, but ties you to LaTeX.

## Common Gotchas

- **Forgot `--citeproc`.** Citations render as literal text: `[@smith2020]`. The `--bibliography` flag alone does nothing without `--citeproc`.
- **Citation key not found.** Pandoc warns `[WARNING] Citation smith2020 not found` and leaves the literal `[@smith2020]` in the output. Check your `.bib` for a typo in the key.
- **Zotero `.bib` exports lose data.** The default Zotero BibTeX export normalizes Unicode aggressively and mangles citation keys. Install the **Better BibTeX** extension (https://retorque.re/zotero-better-bibtex/) for stable, citation-friendly keys (`author2020title` style) and clean Unicode export.
- **CSL file not found.** `pandoc: chicago-author-date.csl: openFile: does not exist`. Either give a full path or place the `.csl` in pandoc's user data directory (`pandoc --version` shows the location, or `--data-dir`). Pandoc only searches the working directory and the data dir.
- **Wrong citation style for your venue.** ACM venues want `acm-siggraph.csl`; IEEE Transactions wants `ieee.csl`; specific journals often have their own. Check the publisher's submission guidelines first; many publishers list their CSL file at the Zotero style repo.
- **Mixed natbib + citeproc.** Don't pass `--citeproc` together with `--natbib` or `--biblatex`. Pandoc 3.9.0.2 accepts the combination without warning or error and the last one specified wins for `cite-method`, but mixing the two pipelines can produce double citations or other surprises. Treat them as mutually exclusive even though the binary doesn't enforce it.
- **Forward references in narrative LaTeX.** With `--natbib`/`--biblatex` you must compile twice (or use `latexmk`) for citation labels to resolve. With `--citeproc`, single-pass works.

## Sources

- Pandoc User's Guide — Citations section: https://pandoc.org/MANUAL.html#citations
- Citation Style Language — official styles repository: https://github.com/citation-style-language/styles
- Zotero Style Repository (searchable): https://www.zotero.org/styles
- CSL specification (entry point — links to versioned specs): https://citationstyles.org/developers/
- Better BibTeX for Zotero (stable citation keys): https://retorque.re/zotero-better-bibtex/
- Pandoc citeproc library source: https://github.com/jgm/citeproc

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
