# API Surface

For pandoc 3.9.0.2 (commit c15e062), "API" is broader than for most CLIs. There are five surfaces a wrapper or downstream user may interact with:

1. **Command-line flags** — the primary user-facing API
2. **Defaults file YAML schema** — declarative form of (1)
3. **Template variables** — the contract between writers and templates
4. **Lua filter API** — `pandoc.*` namespace exposed to Lua scripts
5. **Server / HTTP API** — `pandoc-server` (out of scope for the wrapper, mentioned for completeness)

## 1. CLI flags

Cross-reference: see `cli-interface.md` for the full inventory of ~150 flags grouped by concern, with per-flag source-line citations to `src/Text/Pandoc/App/CommandLineOptions.hs`.

The CLI is the only API the wrapper itself directly invokes — pandoc is shelled out as a subprocess.

## 2. Defaults file YAML schema

`-d FILE` / `--defaults=FILE` loads options from a YAML file. The schema is documented in MANUAL.txt under "Defaults files" (https://pandoc.org/MANUAL.html#defaults-files). Top-level keys map 1:1 to CLI flags; the value type matches the flag's expected argument.

### Key conventions

| YAML key | CLI flag | Value type |
|---|---|---|
| `from` / `reader` | `--from` | string (format spec) |
| `to` / `writer` | `--to` | string (format spec) |
| `output-file` | `--output` | string (path) or `false` for stdout |
| `input-files` | (positional args) | list of strings |
| `data-dir` | `--data-dir` | string |
| `defaults` | `-d` | list of strings (chained defaults files) |
| `metadata` | `--metadata` | map (any YAML structure) |
| `metadata-files` | `--metadata-file` | list of strings |
| `standalone` | `--standalone` | bool |
| `template` | `--template` | string |
| `variables` | `--variable` | map of key → value |
| `wrap` | `--wrap` | `auto` \| `none` \| `preserve` |
| `ascii` | `--ascii` | bool |
| `toc` | `--toc` | bool |
| `toc-depth` | `--toc-depth` | int |
| `number-sections` | `--number-sections` | bool |
| `top-level-division` | `--top-level-division` | `section` \| `chapter` \| `part` (the binary also accepts `default` without erroring, but this is undocumented in `pandoc --help` and the MANUAL — stick to the three documented values) |
| `extract-media` | `--extract-media` | string |
| `resource-path` | `--resource-path` | list of strings |
| `include-in-header` | `--include-in-header` | list of strings |
| `include-before-body` | `--include-before-body` | list of strings |
| `include-after-body` | `--include-after-body` | list of strings |
| `highlight-style` | `--highlight-style` | string (still listed in `pandoc --help` as a primary option; the newer equivalent is `syntax-highlighting`) |
| `syntax-definitions` | `--syntax-definition` | list of strings |
| `dpi` | `--dpi` | int |
| `eol` | `--eol` | `crlf` \| `lf` \| `native` |
| `columns` | `--columns` | int |
| `pdf-engine` | `--pdf-engine` | string |
| `pdf-engine-opts` (plural — defaults-file YAML key) | `--pdf-engine-opt` (singular — CLI flag, repeatable) | list of strings in YAML; one repeated CLI flag per option string |
| `reference-doc` | `--reference-doc` | string |
| `embed-resources` | `--embed-resources` | bool |
| `link-images` | `--link-images` | bool |
| `filters` | `--filter` / `--lua-filter` / `--citeproc` | list of filter specs (see below) |
| `cite-method` | `--natbib` / `--biblatex` / `--citeproc` | `citeproc` \| `natbib` \| `biblatex` |
| `bibliography` | `--bibliography` | string or list of strings |
| `csl` | `--csl` | string |
| `citation-abbreviations` | `--citation-abbreviations` | string |
| `track-changes` | `--track-changes` | `accept` \| `reject` \| `all` |
| `verbosity` | `--verbose` / `--quiet` | `INFO` \| `WARNING` \| `ERROR` |
| `log-file` | `--log` | string |
| `fail-if-warnings` | `--fail-if-warnings` | bool |
| `sandbox` | `--sandbox` | bool |

### Filter spec syntax

The `filters` key takes a list. Each element is either a string (interpreted as a path; `.lua` extension → Lua filter, anything else → JSON filter, the literal `"citeproc"` → built-in citeproc) or an object:

```yaml
filters:
  - citeproc
  - my-filter.lua
  - type: lua
    path: another.lua
  - type: json
    path: pandoc-crossref
  - type: citeproc
```

Source: `src/Text/Pandoc/Filter.hs:46-66` defines `FromJSON Filter`. Both string and object forms are supported.

### Defaults composition

Multiple `-d` flags compose left-to-right. CLI flags override defaults values. A `defaults:` key inside a defaults file chains additional defaults files (resolved against the data dir).

## 3. Template variables

Pandoc templates use the doctemplates library syntax: `$variable$`, `$if(x)$...$endif$`, `$for(x)$...$endfor$`, `$variable.subfield$`, `$it$` (current loop item).

### Variables set automatically by writers

Set by the writer regardless of metadata. Common ones:

- `body` — the document body (rendered)
- `title` — document title
- `subtitle` — document subtitle
- `author` — list of author names (`$for(author)$$author$$sep$, $endfor$`)
- `date` — document date
- `abstract` — document abstract
- `lang` — language code (e.g. `en-US`)
- `dir` — text direction (`ltr` or `rtl`)
- `toc` — true if `--toc` was passed
- `table-of-contents` — the rendered TOC (HTML/LaTeX/etc.)
- `toc-title` — heading for the TOC (translated via `data/translations/`)
- `numbersections` — true if `--number-sections` was passed
- `header-includes` — content from `--include-in-header` files
- `include-before` — content from `--include-before-body` files
- `include-after` — content from `--include-after-body` files
- `pagetitle` — used for `<title>` in HTML
- `title-prefix` — from `--title-prefix`
- `css` — list of stylesheet URLs (from `-c`/`--css`)
- `bibliography` — rendered bibliography section

### Format-specific variables

- HTML: `quotes` (use `<q>` tags), `mathjax`, `katex`, `webtex`, `mathml`, `math` (raw script tag), `highlighting-css`
- LaTeX/Beamer: `documentclass`, `classoption`, `papersize`, `fontsize`, `fontfamily`, `geometry`, `linkcolor`, `urlcolor`, `mainfont`, `sansfont`, `monofont`, `mathfont`, `lang`, `polyglossia-lang`, `babel-lang`, `numbersections`, `secnumdepth`, `links-as-notes`, `lof`, `lot`, `listings`, `colorlinks`, `toc-own-page`
- ConTeXt: `papersize`, `pagesize`, `interfacelanguage`
- EPUB: `cover-image`, `epub-version`, `coverpage`, `titlepage`
- DOCX/ODT/PPTX: variables flow through `--reference-doc`'s style definitions, not template variables

### Setting variables

```bash
# CLI
pandoc -V geometry:margin=1in -V fontsize:12pt input.md -o out.pdf

# Or as JSON for complex values
pandoc --variable-json '{"author":[{"name":"Jeff","affiliation":"47tabs"}]}' ...

# Or as metadata (also passes through to writer)
pandoc -M title="My Doc" -M date="2026-04-19" input.md
```

The difference between `--variable` and `--metadata`:
- `--metadata` writes into the AST's `Meta` field. It can affect the document content (e.g. `--metadata bibliography:refs.bib`).
- `--variable` writes only into the template's variable context. It cannot affect the AST.

Reference: `src/Text/Pandoc/App/CommandLineOptions.hs:300` (`--metadata`), 363 (`--variable`).

## 4. Lua filter API

The `--lua-filter` mechanism executes user Lua code against the document AST. Lua scripts have access to a `pandoc` global with the namespaces below.

Documentation: https://pandoc.org/lua-filters.html

### Main exposed types

All AST node types from `pandoc-types` are exposed as Lua tables:

- `pandoc.Pandoc(blocks, meta)` — document
- `pandoc.Meta(table)`
- **Block constructors**: `pandoc.Para`, `pandoc.Plain`, `pandoc.Header`, `pandoc.CodeBlock`, `pandoc.RawBlock`, `pandoc.BlockQuote`, `pandoc.OrderedList`, `pandoc.BulletList`, `pandoc.DefinitionList`, `pandoc.HorizontalRule`, `pandoc.LineBlock`, `pandoc.Table`, `pandoc.Figure`, `pandoc.Div`
- **Inline constructors**: `pandoc.Str`, `pandoc.Emph`, `pandoc.Strong`, `pandoc.Underline`, `pandoc.Strikeout`, `pandoc.Superscript`, `pandoc.Subscript`, `pandoc.SmallCaps`, `pandoc.Quoted`, `pandoc.Cite`, `pandoc.Code`, `pandoc.Space`, `pandoc.SoftBreak`, `pandoc.LineBreak`, `pandoc.Math`, `pandoc.RawInline`, `pandoc.Link`, `pandoc.Image`, `pandoc.Note`, `pandoc.Span`
- **Helper types**: `pandoc.Attr`, `pandoc.ListAttributes`, `pandoc.Citation`, `pandoc.Cell`, `pandoc.Row`, `pandoc.TableHead`, `pandoc.TableBody`, `pandoc.TableFoot`

### Built-in modules

Each is a sub-namespace under `pandoc`:

| Module | Source | Provides |
|---|---|---|
| `pandoc.utils` | (inline in Module/Pandoc.hs) | `stringify`, `make_sections`, `to_roman_numeral`, `equals`, `sha1`, ... |
| `pandoc.mediabag` | `pandoc-lua-engine/src/Text/Pandoc/Lua/Module/MediaBag.hs` | `insert`, `lookup`, `delete`, `list`, `fetch`, `items` |
| `pandoc.path` | `Module/Path.hs` | `join`, `split`, `directory`, `filename`, `make_relative`, `normalize` |
| `pandoc.system` | `Module/System.hs` | `os`, `arch`, `with_temporary_directory`, `with_working_directory`, `environment` |
| `pandoc.format` | `Module/Format.hs` | `extensions`, `default_extensions`, `from_path`, `parse_format` |
| `pandoc.json` | `Module/JSON.hs` | `decode`, `encode` |
| `pandoc.log` | `Module/Log.hs` | `info`, `warn`, `silence` |
| `pandoc.image` | `Module/Image.hs` | image dimension/format inspection |
| `pandoc.template` | `Module/Template.hs` | `compile`, `apply` |
| `pandoc.layout` | (provided by HsLua's `DocLayout`, surfaced via `Module/Template.hs`) | pretty-printing primitives for building `Doc` values; documented at https://pandoc.org/lua-filters.html under "Module pandoc.layout" |
| `pandoc.structure` | `Module/Structure.hs` | `make_sections`, `table_of_contents` |
| `pandoc.cli` | `Module/CLI.hs` | parse CLI args inside Lua (for custom writers) |
| `pandoc.scaffolding` | `Module/Scaffolding.hs` | building blocks for custom readers/writers |

### Filter return shape

```lua
-- Implicit form: define top-level functions named after AST node types
function Header(el)
  el.level = el.level + 1
  return el
end

-- Explicit form: return a table
return {
  { Header = function(el) ... return el end },
  { Para   = function(el) ... return el end },
}
```

The implicit form runs all collected functions in a single pass. The explicit list-of-tables form runs each table as a separate pass over the AST. Source: `pandoc-lua-engine/src/Text/Pandoc/Lua/Filter.hs:44-50`.

### Reader options inside Lua

Filters get a global `PANDOC_READER_OPTIONS`, `PANDOC_WRITER_OPTIONS`, `PANDOC_DOCUMENT` (the whole `Pandoc`), `FORMAT` (target output format), `PANDOC_VERSION` (a `pandoc.Version` object), and `PANDOC_STATE`. See https://pandoc.org/lua-filters.html#global-variables.

## 5. Server / HTTP API (out of scope)

Pandoc 3.x bundles `pandoc-server` (cabal flag `server`, default `True`). The installed 3.9.0.2 binary reports `Features: +server +lua` so the server is available, but the wrapper does not expose it.

Invoke as: `pandoc server [--port N] [--timeout SECS]` — runs an HTTP server that accepts conversion requests as JSON POST bodies.

The standalone library is published separately: https://hackage.haskell.org/package/pandoc-server.

The server's request schema mirrors the defaults file: a JSON object with keys like `from`, `to`, `text`, `standalone`, `template`, `metadata`, `variables`. Useful for batch/server workloads but not for the v0.1 CLI wrapper.

Source: `pandoc-server/` directory in the source tree.

## Custom writers / readers (out of scope)

Pandoc 3.x supports custom writers and readers in Lua. A Lua file with a `Writer` function or a `Reader` function (plus support functions) can be passed as the `-t`/`-f` value. Source: `pandoc-lua-engine/src/Text/Pandoc/Lua/Custom.hs`. Documented at https://pandoc.org/custom-writers.html and https://pandoc.org/custom-readers.html. Not part of the wrapper's MVP.

## Sources

- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\App\CommandLineOptions.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\App\Opt.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Filter.hs` (lines 41-73 for filter spec serialization)
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\pandoc-lua-engine\src\Text\Pandoc\Lua\Module\` (entire directory)
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\data\templates\default.html5` (sample template — variables visible inline)
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\MANUAL.txt`
- https://pandoc.org/MANUAL.html#defaults-files
- https://pandoc.org/MANUAL.html#templates
- https://pandoc.org/MANUAL.html#variables
- https://pandoc.org/lua-filters.html
- https://pandoc.org/custom-writers.html
- https://pandoc.org/custom-readers.html
- https://hackage.haskell.org/package/pandoc-server
- https://hackage.haskell.org/package/pandoc-types
- https://hackage.haskell.org/package/doctemplates
