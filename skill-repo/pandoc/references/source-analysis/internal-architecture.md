# Internal Architecture

Architecture of pandoc 3.9.0.2 (commit c15e062). Based on direct source inspection of `src/Text/Pandoc/`.

## The reader → AST → writer pipeline

Pandoc's core design is a single in-memory AST (`Pandoc`) that all converters route through. Every conversion is:

```
input bytes
   |
   v
Reader (e.g. readMarkdown)         -- src/Text/Pandoc/Readers/<Format>.hs
   |
   v
Pandoc AST                          -- defined in pandoc-types (separate package)
   |
   v
Transforms (built-in)               -- src/Text/Pandoc/Transforms.hs
  - headerShift          (--shift-heading-level-by)
  - filterIpynbOutput    (--ipynb-output)
  - eastAsianLineBreakFilter
  - applyTransforms      (other normalizations)
   |
   v
Filters (user-supplied, ordered)    -- src/Text/Pandoc/Filter.hs
  - LuaFilter      (--lua-filter)
  - JSONFilter     (--filter)
  - CiteprocFilter (--citeproc, or "citeproc" entry in defaults)
   |
   v
Pandoc AST (modified)
   |
   v
Writer (e.g. writeHtml5String)     -- src/Text/Pandoc/Writers/<Format>.hs
   |
   v
output bytes (Text or ByteString)
```

The pipeline is orchestrated by `convertWithOpts` in `src/Text/Pandoc/App.hs:295-310`. Filters are applied in source-supplied order: see `App.hs:303` (`>=> applyFilters scriptingEngine filterEnv filters [T.unpack format]`).

## The Pandoc AST

Defined in the **separate** package `pandoc-types` (https://github.com/jgm/pandoc-types), imported as `Text.Pandoc.Definition`. The core types:

```haskell
data Pandoc = Pandoc Meta [Block]
data Meta   = Meta { unMeta :: Map Text MetaValue }
data Block  = Plain [Inline]
            | Para [Inline]
            | LineBlock [[Inline]]
            | CodeBlock Attr Text
            | RawBlock Format Text
            | BlockQuote [Block]
            | OrderedList ListAttributes [[Block]]
            | BulletList [[Block]]
            | DefinitionList [([Inline], [[Block]])]
            | Header Int Attr [Inline]
            | HorizontalRule
            | Table Attr Caption [ColSpec] TableHead [TableBody] TableFoot
            | Figure Attr Caption [Block]
            | Div Attr [Block]
data Inline = Str Text
            | Emph [Inline] | Underline [Inline] | Strong [Inline]
            | Strikeout [Inline] | Superscript [Inline] | Subscript [Inline]
            | SmallCaps [Inline] | Quoted QuoteType [Inline]
            | Cite [Citation] [Inline]
            | Code Attr Text | Space | SoftBreak | LineBreak
            | Math MathType Text | RawInline Format Text
            | Link Attr [Inline] Target | Image Attr [Inline] Target
            | Note [Block] | Span Attr [Inline]
```

Filters operate on this AST. The structure is intentionally lossy — for example, fonts and margins are not represented because no portable representation of them exists across all formats.

## Reader registry

`src/Text/Pandoc/Readers.hs:137` declares the readers list:

```haskell
readers :: PandocMonad m => [(Text, Reader m)]
readers = [("native", TextReader readNative)
          ,("json",   TextReader readJSON)
          ,("markdown", TextReader readMarkdown)
          ,("commonmark", TextReader readCommonMark)
          ,...
          ]
```

`getReader` (line 192) does the lookup: takes a `FlavoredFormat` (format name + extension diff), returns the `Reader` plus the resolved `Extensions` set.

`Reader` is a sum type:

```haskell
data Reader m = TextReader       (ReaderOptions -> Sources -> m Pandoc)
              | ByteStringReader (ReaderOptions -> ByteString -> m Pandoc)
```

Binary formats (docx, odt, pptx, xlsx, epub, fb2, ipynb) use `ByteStringReader`. Everything else uses `TextReader`.

## Writer registry

`src/Text/Pandoc/Writers.hs:156` declares the writers list (~64 entries). Lookup via `getWriter` at line 235. `Writer` mirrors `Reader`:

```haskell
data Writer m = TextWriter       (WriterOptions -> Pandoc -> m Text)
              | ByteStringWriter (WriterOptions -> Pandoc -> m ByteString)
```

Binary writers: `docx`, `odt`, `pptx`, `epub`/`epub2`/`epub3`, `chunkedhtml`. PDF is special — there is no PDF writer in `writers`; PDF generation goes through `Text.Pandoc.PDF.makePDF` which produces a LaTeX/HTML/Typst source and shells out to a `--pdf-engine`.

## Filter pipeline

`src/Text/Pandoc/Filter.hs` defines:

```haskell
data Filter = LuaFilter FilePath
            | JSONFilter FilePath
            | CiteprocFilter
```

`applyFilters` (line 76) folds filters left-to-right. Each filter either:
- runs a Lua script via `engineApplyFilter` from the scripting engine (line 90)
- shells out to a JSON filter executable via `JSONFilter.apply` (line 88)
- runs the in-process citeproc processor via `processCitations` (line 92)

### JSON filters (the `--filter` mechanism)

A JSON filter is any executable. Pandoc serializes the AST to JSON on stdin, runs the filter with the output format as `argv[1]`, and parses JSON from stdout. Filters can be written in any language. The `pandocfilters` Python package and the Haskell `pandoc-filter` package wrap the protocol.

`src/Text/Pandoc/Filter/JSON.hs` — implementation. The protocol contract is the JSON serialization of `Pandoc` from `pandoc-types`.

### Lua filters (the `--lua-filter` mechanism)

Pandoc bundles its own Lua 5.4 interpreter (`pandoc-lua-engine` package, built on `HsLua`). A Lua filter is a Lua script that returns a table of element-name → function callbacks:

```lua
function Header(el)
  if el.level == 1 then el.level = 2 end
  return el
end

function Str(el)
  return pandoc.Str(string.upper(el.text))
end
```

The implicit `_ENV` form (above) collects functions named after AST node types. The explicit form is `return { Header = function(el) ... end, ... }`.

Loader entry: `pandoc-lua-engine/src/Text/Pandoc/Lua/Filter.hs:26` (`runFilterFile`). The full Lua module surface is exposed in `pandoc-lua-engine/src/Text/Pandoc/Lua/Module/`:

- `Pandoc.lua` — the main `pandoc.*` namespace
- `Format.lua` — `pandoc.format.*`
- `Image.lua` — image utilities
- `JSON.lua` — JSON encode/decode
- `Log.lua` — `pandoc.log.*`
- `MediaBag.lua` — `pandoc.mediabag.*`
- `Path.lua` — path manipulation (`pandoc.path.*`)
- `Structure.lua` — `pandoc.structure.*` (make_sections, table_of_contents, ...)
- `System.lua` — system info (`pandoc.system.*`)
- `Template.lua` — template compilation/rendering

### Filter ordering and citeproc

Filters listed by `--filter`/`--lua-filter` run in CLI order. `--citeproc` injects a `CiteprocFilter` at the position it appeared. If you need citation processing AFTER another filter (e.g. one that adds citations dynamically), write `--lua-filter foo.lua --citeproc` — order matters.

## Templates

Templates use the **doctemplates** library (https://hackage.haskell.org/package/doctemplates), with `$variable$`, `$if(x)$...$endif$`, `$for(x)$...$endfor$` syntax. Bundled defaults live in `data/templates/`.

`src/Text/Pandoc/Templates.hs` re-exports `compileTemplate` and `renderTemplate` from doctemplates. Pandoc's customizations:

- `compileTemplate ("templates/default." <> writerName)` (line 141) — load the default template for a given writer, falling back through the data-dir search path
- Templates have access to writer-set variables (e.g. `body`, `title`, `author`, `toc`, `header-includes`) plus anything from `--variable` / `--variable-json` / metadata.

Inspect a default with: `pandoc -D html5` or `pandoc --print-default-template=latex`.

For binary writers (docx, odt, pptx), the analog is `--reference-doc`: a sample document whose styles are copied into the output. The bundled defaults are `data/docx/reference.docx`, `data/odt/reference.odt`, `data/pptx/reference.pptx`.

## Citations (citeproc)

As of pandoc 2.11 (released 2020), `pandoc-citeproc` was retired and citeproc was integrated into the main pandoc binary. `src/Text/Pandoc/Citeproc.hs` is the in-process citeproc entry point.

Flow:

1. Read bibliography files listed in metadata `bibliography:` or via `--bibliography`. Supported readers in `Citeproc.hs:14-21`: BibTeX, BibLaTeX, CSL JSON, CSL YAML, RIS, EndNote XML.
2. Parse the CSL style file from `--csl` (default: Chicago author-date from `data/default.csl`).
3. Walk the AST (`Text.Pandoc.Walk`) collecting `Cite` nodes.
4. `processCitations` (Citeproc.hs:8) renders each citation through the `citeproc` library and replaces `Cite` nodes with formatted inlines.
5. Append a "References" section if the template has a `$bibliography$` placeholder.

`--natbib` and `--biblatex` skip citeproc entirely and emit raw LaTeX `\cite{}` commands for the LaTeX/Beamer writers to handle.

## The `data/` directory

| Path | Contents |
|---|---|
| `data/templates/` | 61 default templates, one per writer (e.g. `default.html5`, `default.latex`, `default.beamer`, `default.docbook5`) plus shared `styles.html`, `affiliations.jats`, `common.latex`, etc. |
| `data/translations/` | 107 YAML files (one per language) with translations for words like "Figure", "Table", "Abstract" used by writers |
| `data/default.csl` | Default CSL style (Chicago author-date). Single file at the root of `data/`; there is no `data/csl/` subdirectory. |
| `data/abbreviations` | English sentence-final abbreviations for the markdown reader (Mr., Dr., e.g., etc.) |
| `data/init.lua` | Lua scaffolding loaded at engine startup |
| `data/creole.lua` | Creole reader implementation in Lua |
| `data/docx/`, `data/odt/`, `data/pptx/`, `data/dzslides/` | Binary reference documents and the file skeletons for binary writers |
| `data/bash_completion.tpl` | Template for `--bash-completion` output |
| `data/docbook-entities.txt` | DocBook entity table |
| `data/epub.css` | Default CSS for EPUB output |

User overrides in `--data-dir` (or `$XDG_DATA_HOME/pandoc` on Linux, `~/Library/Application Support/pandoc` on macOS, `%APPDATA%\pandoc` on Windows) are tried first, falling back to bundled.

## Key source locations summary

| Concern | File | Line |
|---|---|---|
| CLI option list | `src/Text/Pandoc/App/CommandLineOptions.hs` | 272 |
| Conversion orchestration | `src/Text/Pandoc/App.hs` | 295 (`convertWithOpts`) |
| Reader registry | `src/Text/Pandoc/Readers.hs` | 137 |
| Writer registry | `src/Text/Pandoc/Writers.hs` | 156 |
| Filter pipeline | `src/Text/Pandoc/Filter.hs` | 76 (`applyFilters`) |
| Lua filter loader | `pandoc-lua-engine/src/Text/Pandoc/Lua/Filter.hs` | 26 |
| Citeproc | `src/Text/Pandoc/Citeproc.hs` | 8 (`processCitations`) |
| Template system | `src/Text/Pandoc/Templates.hs` | (re-exports doctemplates) |
| PDF generation | `src/Text/Pandoc/PDF.hs` | 76 (`makePDF`) |
| Highlighting | `src/Text/Pandoc/Highlighting.hs` | (wraps `skylighting`) |
| Self-contained HTML | `src/Text/Pandoc/SelfContained.hs` | (`makeSelfContained`) |

## Sources

- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\App.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Readers.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Writers.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Filter.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Citeproc.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\pandoc-lua-engine\src\Text\Pandoc\Lua\Filter.hs`
- https://github.com/jgm/pandoc-types (AST package)
- https://hackage.haskell.org/package/doctemplates
- https://pandoc.org/MANUAL.html#templates
- https://pandoc.org/lua-filters.html
- https://pandoc.org/MANUAL.html#citations
