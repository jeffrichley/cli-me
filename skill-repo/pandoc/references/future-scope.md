# pandoc Skill — v0.2 Deferred Features

The MVP scope (convert, citations, templates, filters, info) covers Jeff's
stated use cases (47 Tabs pitches, PhD drafts, NIWC docs). Everything below
is intentionally out of scope for the first release. This file is the
authoritative backlog — keep it in sync with the v0.2 task list.

## Slides

Older HTML slide writers remain deferred:
- `slidy`
- `s5`
- `dzslides`
- `slideous`

Deeper slide-specific helpers also remain deferred:
- Speaker notes helpers
- Background-image helpers
- Two-column layout helpers
- Named theme/transition wrapper flags

## Jupyter Notebook Formats

- `--from ipynb`, `--to ipynb`
- Roundtripping markdown ↔ ipynb (preserving outputs vs stripping them)
- Cell metadata preservation
- Math rendering for notebook outputs
- Required for academic / research workflows

## Exotic Format Pairs

Each adds new reader/writer test surface; defer until demand:
- MediaWiki, DokuWiki
- Jira (markup), Confluence
- Org-mode (Emacs)
- AsciiDoc (input + output)
- RST (reStructuredText)
- OPML
- Textile
- Muse
- FB2 (FictionBook)
- ConTeXt
- man pages (groff_man)

## Custom Lua-Based Writers

`--writer=path/to/writer.lua` lets users author entirely new output formats
in Lua. Pandoc exposes its AST + writer API to Lua.
- Documented at https://pandoc.org/custom-writers.html
- Useful for shipping custom output formats (Discord-flavored markdown, etc.)
- Substantial wrapper work: validate the Lua writer file, surface error
  messages from broken writers, document the AST traversal API for users

## Advanced Filter Patterns

Beyond pandoc-crossref:
- `panflute` — Python filter framework, easier than raw pandocfilters
- JSON filter pipeline composition
- Multi-filter chaining patterns and ordering pitfalls
- Performance considerations (in-process Lua vs subprocess JSON)
- Citeproc + filter interaction edge cases
- Filter-induced AST corruption debugging

## Deep Template Authoring

The MVP wraps `--template` and `--reference-doc` usage. Out of scope:
- Creating templates from scratch (vs editing the default)
- Pandoc template syntax mastery: variables, conditionals, loops, partials
- Per-format template differences (LaTeX preamble vs HTML head vs DOCX styles)
- Template inheritance / composition
- The `pandoc --print-default-template=FORMAT` introspection workflow

## Math Rendering Modes

The MVP doesn't surface math-rendering choice. Out of scope:
- `--mathjax[=URL]` — MathJax in HTML output
- `--katex[=URL]` — KaTeX in HTML output (faster than MathJax)
- `--webtex[=URL]` — render math as PNG via web service
- `--mathml` — MathML in HTML/EPUB
- `--gladtex` — GladTeX preprocessor for math
- `--mimetex[=URL]` — MimeTeX rendering
- Format-specific math handling: DOCX OMath, EPUB MathML, LaTeX native

## Code Highlighting Customization

The MVP uses pandoc's default highlighting (Skylighting library):
- `--syntax-definition=FILE` — KDE syntax XML for new languages
- `--highlight-style=NAME|FILE` — pre-built styles or KDE theme files
- `--no-highlight` — disable highlighting entirely
- LaTeX `listings` package integration (`--listings`)
- Fenced code attribute syntax (`{.python .numberLines startFrom="10"}`)

## Extension-Flag Mastery

Pandoc's `+ext-ext` syntax controls hundreds of per-format behaviors:
- Per-format extension defaults
- GFM (GitHub-Flavored Markdown) vs CommonMark vs pandoc-markdown trade-offs
- Discovering extensions: `pandoc --list-extensions=FORMAT`
- Common toggles: `+yaml_metadata_block`, `+raw_html`, `-implicit_figures`,
  `+pipe_tables`, `+grid_tables`, `+simple_tables`, `+tex_math_dollars`

## NOT Planned (Even for v0.2)

### pandoc-server

`pandoc-server` mode (HTTP API for converting documents) doesn't fit Jeff's
one-shot conversion use cases. Demoted from "v0.2" to "if a use case
emerges." Pandoc 3.9.0.2 includes the `+server` feature flag, so the binary
can serve HTTP requests, but wrapping that in cli-me would be a different
shape of skill.

## When To Promote v0.2 → v0.3 / next-MVP

Triggers for promoting any of the above into the next release:
- Concrete use case from Jeff's pipeline
- An adversarial review or QA cycle that surfaces the gap
- A user (agent or human) requesting the feature

Don't pre-build because "it's important." Wait for demand signal.
