# Metadata and Frontmatter

## When to Use

Use this technique whenever you need to feed structured information into pandoc — title, author, date, abstract, keywords, custom variables for templates, citation defaults, language settings — instead of repeating it on every command line. Defaults files take it further: a single YAML file encapsulates every pandoc option for a project, so you can convert with `pandoc --defaults preset.yaml input.md`.

This is the right place to set up reusable presets per project: a "PhD chapter" preset, a "47 Tabs onepager" preset, a "NIWC report" preset. Combine with [templates](templates.md) for branded output and [citations](citations.md) for bibliography defaults.

## Technique

### YAML Metadata Blocks

A YAML metadata block sits at the top of a markdown document, fenced by `---`:

```yaml
---
title: "Bayesian Methods in Human-Robot Interaction"
subtitle: "A PhD Dissertation Chapter"
author: [Jeff Richley, Co-Author Name]
date: 2026-04-18
abstract: |
  This chapter explores Bayesian inference for HRI, with particular
  attention to belief updating during multi-turn dialog.
keywords: [bayesian inference, hri, dialog systems]
lang: en-US
bibliography: refs.bib
csl: apa.csl
---

# Introduction

The chapter begins here...
```

Rules:

- The block must start at line 1 (or after a previous metadata block).
- The opening `---` and closing `---` (or `...`) must be on their own lines, with no surrounding whitespace.
- Multiple metadata blocks merge — **later wins on conflict** (verified at runtime: two input docs with conflicting `title:` resolve to the second doc's title; two `--metadata-file` flags resolve to the second file's value).
- Markdown is allowed inside string values; pandoc parses it.

### Standard Variables That Templates Use

The default templates (and most third-party templates) honor a fixed set of variable names. Set them in YAML, with `--metadata`, or with `--variable`:

| Variable | Type | Used for |
|----------|------|----------|
| `title` | string | Document title (cover page, `<title>`, PDF metadata) |
| `subtitle` | string | Subtitle below the title |
| `author` | string or list | Author name(s) |
| `date` | string | Publication date |
| `abstract` | string | Abstract (rendered before body in academic templates) |
| `keywords` | list | PDF metadata, `<meta name="keywords">` |
| `lang` | string | BCP 47 code (`en-US`, `de-DE`, etc.) |
| `mainfont` / `sansfont` / `monofont` | string | Fonts (xelatex/lualatex only) |
| `fontsize` | string | `10pt`, `11pt`, `12pt` |
| `geometry` | string or list | LaTeX geometry package args (`margin=1in`) |
| `linkcolor` / `urlcolor` | string | Color of links in PDF |
| `links-as-notes` | boolean | Render links as footnotes (PDF) |
| `toc` / `toc-depth` | boolean / integer | Include table of contents and depth |
| `numbersections` | boolean | Number `# Heading` levels |
| `documentclass` | string | LaTeX document class (`article`, `report`, `book`) |
| `papersize` | string | `a4`, `letter`, etc. |

Custom variables work too — any key you set is available as `$mykey$` inside a custom template.

### CLI Overrides

Three flags control metadata from the command line:

| Flag | Effect | Visibility |
|------|--------|------------|
| `--metadata KEY=VAL` (`-M`) | Set/override a metadata field. Becomes part of the document. | Filters and templates both see it. |
| `--metadata-file FILE` | Load YAML/JSON file as additional metadata. | Filters and templates both see it. |
| `--variable KEY=VAL` (`-V`) | Set a template variable only. | Only the template sees it; filters do not. |

Priority order for metadata (highest wins): `-M` / `--metadata` on the command line, then YAML frontmatter in the document, then `--metadata-file`. Per the MANUAL section on `--metadata-file`: "Metadata values specified inside the document, or by using -M, overwrite values specified with this option." Verified at runtime: when `-M title=A`, frontmatter `title: B`, and `--metadata-file` with `title: C` are all set, `A` wins; with only frontmatter `B` and metadata-file `C`, `B` wins.

Use `-M` for things filters care about (like `bibliography`); use `-V` for pure presentation variables that filters don't need to see. `--variable` lives in a separate variable namespace from metadata, so the priority discussion above is about metadata only — `-V` always wins for template variables since metadata-file/frontmatter don't write into the variable namespace.

### Metadata Files

`--metadata-file project.yaml` loads a freestanding YAML file as if it were a frontmatter block. Useful for sharing metadata across many documents in a project:

```yaml
# project-meta.yaml
author: Jeff Richley
affiliation: 47 Tabs Inc.
copyright: "© 2026 47 Tabs Inc. All rights reserved."
lang: en-US
```

```bash
pandoc onepager.md --metadata-file project-meta.yaml -o onepager.pdf
```

Multiple files merge in order; later files override earlier ones.

### Defaults Files

A defaults file (`--defaults FILE`) encapsulates **every** pandoc CLI option in a single YAML file. Each top-level key maps to a CLI flag. This is the right way to ship reusable conversion presets.

The full schema lives at https://pandoc.org/MANUAL.html#defaults-files. Common keys:

| YAML key | CLI equivalent |
|----------|----------------|
| `from` / `reader` | `--from` |
| `to` / `writer` | `--to` |
| `output-file` | `-o` |
| `input-files` | positional inputs |
| `standalone` | `--standalone` |
| `template` | `--template` |
| `reference-doc` | `--reference-doc` |
| `pdf-engine` | `--pdf-engine` |
| `bibliography` | `--bibliography` |
| `csl` | `--csl` |
| `citeproc` | `--citeproc` |
| `filters` | `--lua-filter` and `--filter` (mixed list) |
| `metadata` | `--metadata` (as a map) |
| `metadata-files` | `--metadata-file` |
| `variables` | `--variable` (as a map) |
| `toc` / `toc-depth` | `--toc` / `--toc-depth` |
| `number-sections` | `--number-sections` |
| `resource-path` | `--resource-path` |
| `include-in-header` | `--include-in-header` |

CLI flags override matching keys in the defaults file. Defaults files chain: `--defaults a.yaml --defaults b.yaml` applies both, with `b` overriding `a`.

### Defaults File vs Metadata File

Easy to confuse:

- **Defaults file** = pandoc's runtime configuration (what to do). Top-level keys are CLI option names.
- **Metadata file** = document content metadata (what the document is). Top-level keys are document variables (`title`, `author`, etc.).

A defaults file can include a `metadata:` map, which is the same as passing a metadata file. But you can't put pandoc options in a metadata file.

## CLI Commands

**Markdown with frontmatter, no extra flags:**

`paper.md`:
```markdown
---
title: "A Brief Note"
author: Jeff Richley
date: 2026-04-18
---

# Section 1

Content here.
```

```bash
pandoc paper.md -o paper.pdf --pdf-engine=xelatex
```
Verify: PDF cover area shows the title, author, and date pulled from the frontmatter.

**Override frontmatter from CLI:**
```bash
pandoc paper.md -o paper-v2.pdf --pdf-engine=xelatex \
  --metadata title="A Brief Note (Revised)" \
  --metadata date=2026-04-19
```
Verify: PDF title says "A Brief Note (Revised)" — frontmatter `title` was overridden.

**Shared metadata file across multiple docs:**

`project-meta.yaml`:
```yaml
author: Jeff Richley
affiliation: 47 Tabs Inc.
lang: en-US
geometry: margin=1in
mainfont: Inter
```

```bash
pandoc onepager-A.md --metadata-file project-meta.yaml -o A.pdf --pdf-engine=xelatex
pandoc onepager-B.md --metadata-file project-meta.yaml -o B.pdf --pdf-engine=xelatex
pandoc onepager-C.md --metadata-file project-meta.yaml -o C.pdf --pdf-engine=xelatex
```
Verify: all three PDFs share the same author, affiliation, and font.

**Variables-only override (template-visible, filter-invisible):**
```bash
pandoc paper.md \
  --pdf-engine=xelatex \
  -V geometry:margin=0.5in \
  -V linkcolor:blue \
  -V mainfont="Source Serif 4" \
  -o paper.pdf
```
Verify: PDF has narrow margins, blue links, and the specified body font.

**Defaults file for a "PhD chapter" preset:**

`phd-chapter.yaml`:
```yaml
from: markdown
to: pdf
pdf-engine: xelatex
standalone: true
toc: true
toc-depth: 2
number-sections: true
citeproc: true
bibliography: refs.bib
csl: apa.csl
filters:
  - type: json
    path: pandoc-crossref
metadata:
  documentclass: report
  fontsize: 11pt
  papersize: letter
  lang: en-US
variables:
  geometry: margin=1in
  mainfont: "Source Serif 4"
  monofont: "JetBrains Mono"
  linkcolor: "MidnightBlue"
  links-as-notes: true
include-in-header:
  - phd-header.tex
```

```bash
pandoc --defaults phd-chapter.yaml chapter-3.md -o chapter-3.pdf
```
Verify: PDF has TOC, numbered sections, APA-formatted citations, crossref-numbered figures, custom fonts and link colors.

**Override one option of a defaults file from CLI:**
```bash
pandoc --defaults phd-chapter.yaml chapter-4.md \
  --csl ieee.csl \
  -o chapter-4.pdf
```
Verify: same as above but citations use IEEE style instead of APA.

**Defaults file for NIWC DOCX deliverable:**

`niwc-docx.yaml`:
```yaml
from: markdown
to: docx
reference-doc: niwc-template.docx
citeproc: true
bibliography: niwc-refs.bib
csl: ieee.csl
metadata:
  classification: "UNCLASSIFIED"
  distribution: "Distribution Statement A"
  lang: en-US
```

```bash
pandoc --defaults niwc-docx.yaml report.md -o "NIWC-PAC-TR-2026-042.docx"
```
Verify: DOCX opens in Word with NIWC styles, IEEE citations, and a populated reference section.

**Inspect what metadata pandoc sees:**
```bash
pandoc paper.md --metadata-file project-meta.yaml -t native | head -30
```
Verify: output begins with `Pandoc (Meta {unMeta = fromList [...]})` listing every metadata key/value pandoc resolved.

## Under the Hood

YAML metadata blocks are parsed by pandoc's reader before any other content. The result is a `Meta` map (Haskell `Map Text MetaValue`) attached to the `Pandoc` AST root. `MetaValue` is a sum type covering strings, booleans, lists, maps, and arbitrary inline/block content (so a metadata `abstract:` can contain markdown).

`--metadata-file` is implemented by parsing the file as YAML and merging it into the `Meta` map *before* frontmatter, with frontmatter winning on conflict. `--metadata KEY=VAL` parses the value as YAML (so `--metadata foo=true` gives a boolean, not a string) and inserts directly with highest priority.

`--variable` is similar but skips the document `Meta` map entirely. Variables go into a separate map that only the template engine consults. Filters never see them.

Defaults files (`--defaults`) are parsed once at startup. Pandoc maps each YAML key to its corresponding CLI option, populates the option set, and then proceeds as if you had typed the long-form flags. CLI flags applied alongside `--defaults` override the file's settings field-by-field. Server-only options (`--port`, `--ip`) are excluded from defaults files for security reasons.

For metadata specifically, the merge order (verified against the binary on 3.9.0.2) is: `--metadata-file` is applied first, then frontmatter overrides it, then `-M` / `--metadata` from the CLI overrides both. `--variable` writes into a separate template-variable namespace and does not participate in the metadata merge. See the MANUAL `--metadata-file` paragraph (which says "Metadata values specified inside the document, or by using -M, overwrite values specified with this option") and https://pandoc.org/MANUAL.html#defaults-files for the defaults-file layering.

## Common Gotchas

- **Frontmatter not at line 1.** A blank line above `---` makes pandoc treat it as a horizontal rule, not metadata. Frontmatter silently ignored; `$title$` renders empty.
- **Closing `---` vs `...`.** Both work. But a stray `---` later in your document might accidentally open a second metadata block. Use `...` to close if you have horizontal rules elsewhere.
- **YAML quoting.** Unquoted strings starting with `:`, `&`, `*`, `?`, `|`, `>`, `[`, `{`, `#`, `!` are YAML directives. Quote any value starting with these: `title: "Q4: Results"`.
- **`-V` vs `-M` confusion.** `-V toc` (variable) sets a template flag; `-M toc=true` (metadata) sets it in the document model. Most users want `-M` so filters see the value too.
- **Repeating `--metadata` for lists.** `-M author=Jeff -M author=Sam` does not produce a list — the second overwrites the first. Use a metadata file or frontmatter for lists. (Server-only options like `port:` and `ip:` are rejected entirely.)
- **Date formats.** YAML `date: 2026-04-18` is parsed as a date. For non-ISO formats, quote: `date: "April 18, 2026"`.
- **Windows path separators in defaults files.** Use forward slashes (`C:/path/file.bib`) — backslashes need escaping (`C:\\path\\file.bib`).
- **Filters key in defaults files.** The `filters:` list takes objects with `type:` (`json` or `lua`) and `path:`. A bare string is parsed as a JSON filter. Lua filters need explicit `type: lua`.

## Sources

- Pandoc User's Guide — Metadata blocks: https://pandoc.org/MANUAL.html#metadata-blocks
- Pandoc User's Guide — Defaults files (the full schema): https://pandoc.org/MANUAL.html#defaults-files
- Pandoc User's Guide — Variables: https://pandoc.org/MANUAL.html#variables
- YAML 1.2 specification: https://yaml.org/spec/1.2.2/
- Pandoc User's Guide — `--metadata` and `--variable` options: https://pandoc.org/MANUAL.html#general-options

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
