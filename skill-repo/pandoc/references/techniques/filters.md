# Filters

## When to Use

Use filters when you need to transform document content in ways pandoc doesn't support out of the box: numbering and cross-referencing figures/equations/tables, applying custom block styling, processing images, generating author affiliations from a YAML list, lowercasing all headings, wrapping content in custom HTML divs, or anything else that requires walking the document AST.

The most common filter in academic writing is **pandoc-crossref** — it adds proper figure/equation/table numbering with `[@fig:label]` style cross-references. Almost every PhD draft needs it.

For citations, prefer the built-in `--citeproc` over a filter — see [citations](citations.md).

## Technique

### The Filter Pipeline

A pandoc invocation runs as `reader → AST → [filters in order] → writer`. Filters are AST-to-AST functions that pandoc applies between parsing and writing. Each filter sees the AST as left by the previous filter, so order matters.

CLI flags `--lua-filter`, `--filter`, and `--citeproc` can appear repeatedly and execute in the order given:

```bash
pandoc draft.md \
  --lua-filter renumber-figures.lua \
  --filter pandoc-crossref \
  --citeproc \
  --bibliography refs.bib \
  -o draft.pdf
```

This runs `renumber-figures.lua` first, then `pandoc-crossref`, then `--citeproc`. Citeproc must run **after** content filters that add or modify references — otherwise it can't see the citations they introduced.

### Lua Filters (Recommended)

Pandoc has a Lua interpreter built into the binary. `--lua-filter file.lua` runs a Lua script against the AST in-process — no subprocess, no JSON serialization, fast. This is the path you should use unless you have a strong reason to write a JSON filter.

A Lua filter is a Lua file that returns a table mapping AST element types to functions:

```lua
-- uppercase-headings.lua
function Header(el)
  return pandoc.walk_block(el, {
    Str = function(s) return pandoc.Str(string.upper(s.text)) end
  })
end
```

The walker function must match the element kind: `pandoc.walk_block` for `Block` elements (`Header`, `Para`, `Div`, etc.), `pandoc.walk_inline` for `Inline` elements (`Span`, `Link`, `Emph`, etc.). Passing a `Header` (a Block) to `walk_inline` errors with `object has no __toinline metamethod`.

Pandoc walks the AST and calls each handler for the matching element type. Return the modified element to replace it; return `nil` to leave it unchanged; return an empty list `{}` to delete it.

The full Lua API is documented at https://pandoc.org/lua-filters.html. Built-in modules cover:

- `pandoc.*` — element constructors (`pandoc.Str`, `pandoc.Header`, `pandoc.Image`, etc.)
- `pandoc.utils` — helpers (`stringify`, `sha1`, `to_roman_numeral`)
- `pandoc.mediabag` — manipulate embedded media
- `pandoc.layout` — pretty-printing
- `pandoc.system` — file I/O, environment access
- `pandoc.path` — path manipulation (cross-platform)

### JSON Filters (External Programs)

`--filter PROG` runs `PROG` as a subprocess. Pandoc serializes the AST to JSON on stdin, the program reads it, transforms it, writes the modified JSON to stdout, and pandoc deserializes. The program can be in any language; bindings exist for Python (`panflute`, `pandocfilters`), Haskell (`pandoc-types`), JavaScript, Ruby, etc.

Subprocess startup cost is real (~50ms per filter per invocation). For one-shot conversions it doesn't matter; for batch processing thousands of files it adds up. Lua filters have zero startup cost.

`pandoc-crossref` is the most widely used JSON filter. Install via:

```bash
# Cabal (Haskell package manager)
cabal install pandoc-crossref

# Or download a prebuilt binary
# https://github.com/lierdakil/pandoc-crossref/releases
```

Verify with `pandoc-crossref --version`. The binary must be on `PATH`, or pass an absolute path: `--filter /usr/local/bin/pandoc-crossref`.

### pandoc-crossref Syntax

Define labeled figures, equations, and tables in markdown:

```markdown
![A diagram of the architecture.](arch.png){#fig:arch}

$$ E = mc^2 $$ {#eq:einstein}

| Col 1 | Col 2 |
|-------|-------|
| a     | b     |

: Sample data. {#tbl:sample}
```

Reference them inline:

| Markdown | Renders as |
|----------|-----------|
| `[@fig:arch]` | `fig. 1` |
| `[@eq:einstein]` | `eq. 1` |
| `[@tbl:sample]` | `tbl. 1` |
| `[@fig:arch; @fig:flow]` | `figs. 1, 2` |
| `@fig:arch` | `fig. 1` (no parens) |

The crossref filter scans for the `{#fig:label}` attributes, assigns numbers, and rewrites references. Labels must be unique across the document.

### Filter Ordering Rules

Three rules to internalize:

1. **Content-mutating filters before citeproc.** Otherwise citations introduced by your filter get rendered as raw `[@key]` text.
2. **pandoc-crossref before citeproc.** Crossref shares the `[@key]` syntax for refs; if citeproc runs first, your `[@fig:label]` references get treated as missing citation keys.
3. **Numbering filters last among content filters.** Otherwise a later filter that adds a figure throws off the count.

A safe canonical order for an academic document:

```bash
pandoc draft.md \
  --lua-filter wrap-images.lua \
  --filter pandoc-crossref \
  --citeproc \
  --bibliography refs.bib \
  --csl apa.csl \
  -o draft.pdf
```

## CLI Commands

**Run a Lua filter:**
```bash
pandoc draft.md --lua-filter uppercase-headings.lua -o draft.html
```
Verify: every `# Heading` in source becomes `<h1>HEADING</h1>` in HTML.

**Five-line Lua filter that wraps every image in a centered span:**

Save as `center-images.lua`:
```lua
function Image(el)
  return pandoc.Span({el}, {class = "centered"})
end
```

```bash
pandoc draft.md --lua-filter center-images.lua -s -o draft.html
```
Verify: HTML output shows `<span class="centered"><img ...></span>` around every image, both inline and inside figures.

`Image` is an `Inline` node, so its handler must return `Inline` (or a list of inlines) — returning a `Block` like `Div` errors with `object has no __toinline metamethod`. To wrap *figures* (standalone images that pandoc promoted to `Figure` blocks) in a centered `Div` instead, target the block:

```lua
function Figure(el)
  return pandoc.Div({el}, {class = "centered"})
end
```

**Lua filter that uppercases all headings (the MWE):**

Save as `upper-headings.lua`:
```lua
function Header(el)
  return pandoc.walk_block(el, {
    Str = function(s) return pandoc.Str(string.upper(s.text)) end
  })
end
```

(`Header` is a `Block`, so use `pandoc.walk_block`. Verified at runtime against pandoc 3.9.0.2 — `# hello world` → `HELLO WORLD`.)

```bash
pandoc draft.md --lua-filter upper-headings.lua -t plain
```
Verify: heading text appears in all caps in the plain-text output.

**pandoc-crossref for a PhD chapter (figures, equations, tables, citations):**
```bash
pandoc thesis-ch3.md \
  --filter pandoc-crossref \
  --citeproc \
  --bibliography refs.bib \
  --csl apa.csl \
  --pdf-engine=xelatex \
  -o thesis-ch3.pdf
```
Verify: PDF figures and equations are numbered (`Figure 1:`, `Equation 1`, etc.); references like `[@fig:arch]` render as `fig. 1`; bibliography appears at end.

**Multiple filters in pipeline (custom Lua + crossref + citeproc):**
```bash
pandoc thesis.md \
  --lua-filter strip-comments.lua \
  --lua-filter expand-acronyms.lua \
  --filter pandoc-crossref \
  --citeproc \
  --bibliography refs.bib \
  -o thesis.pdf
```
Verify: comments are stripped, acronyms expanded on first use, figures numbered, citations rendered. The order is documented above the command for the next person to read.

**Inspect the AST that filters see (debug helper):**
```bash
pandoc draft.md -t json | python -m json.tool | head -50
```
Verify: prints a JSON tree of `Pandoc`/`Para`/`Header`/etc. nodes. This is exactly what JSON filters consume.

**Run a Python filter using panflute:**

Save as `figcount.py`:
```python
#!/usr/bin/env python3
import panflute as pf

def action(elem, doc):
    if isinstance(elem, pf.Image) and elem.identifier.startswith('fig:'):
        doc.figcount = getattr(doc, 'figcount', 0) + 1

def finalize(doc):
    pf.debug(f"Total figures: {doc.figcount}")

if __name__ == '__main__':
    pf.run_filter(action, finalize=finalize)
```

```bash
pip install panflute
chmod +x figcount.py
pandoc draft.md --filter ./figcount.py -o draft.pdf
# On Windows: pandoc draft.md --filter "python figcount.py" -o draft.pdf
```
Verify: stderr shows `Total figures: N`.

**A Lua filter that counts words and stores it in document metadata:**

Save as `wordcount.lua`:
```lua
local count = 0

function Str(el)
  count = count + 1
end

function Pandoc(doc)
  doc.meta.wordcount = pandoc.MetaString(tostring(count))
  return doc
end
```

```bash
pandoc draft.md --lua-filter wordcount.lua -t markdown | head
```
Verify: output frontmatter contains `wordcount: 1234` (or whatever the count is).

## Under the Hood

The pandoc AST is a Haskell algebraic data type with two main node families: `Block` (paragraphs, headings, code blocks, lists, tables, figures) and `Inline` (string fragments, emphasis, links, images, citations). The full type definition lives in the `pandoc-types` package: https://hackage.haskell.org/package/pandoc-types.

Lua filters work because pandoc embeds the Lua 5.4 interpreter and exposes the AST through a Lua-side mirror of those types. When pandoc loads a Lua filter, it scans for top-level functions named after element types (`Header`, `Para`, `Image`, `Str`, etc.) plus the special `Pandoc` (whole document) and `Meta` (metadata) handlers. It then walks the AST and calls each handler when it encounters a matching node.

JSON filters use the same AST but communicate via JSON over stdin/stdout. Pandoc serializes the entire document to JSON, spawns the filter, pipes JSON in, reads JSON out, deserializes. Each `--filter` flag spawns one subprocess per pandoc invocation.

`pandoc-crossref` reads the AST, walks for image/equation/table nodes with identifiers matching `fig:`, `eq:`, `tbl:`, assigns sequential numbers, builds a label-to-number map, and walks again to replace `Cite` nodes with rendered references. Output is a transformed AST passed to the next filter or the writer.

The Lua interpreter runs in-process, sharing pandoc's memory. Filter functions can mutate elements in place or return new ones. The walking strategy is depth-first; for `Block` handlers, pandoc has already processed all child inlines, so `el.content` reflects post-filter inline state.

## Common Gotchas

- **Filter not found.** `pandoc: pandoc-crossref: createProcess: does not exist`. The filter binary isn't on `PATH`. Either install it correctly, add its directory to `PATH`, or use an absolute path with `--filter`.
- **Wrong filter order with citeproc.** Symptom: `[@fig:arch]` renders as a missing citation warning instead of a figure number. Move `--filter pandoc-crossref` before `--citeproc`.
- **Two filters interpret `[@key]` differently.** pandoc-crossref and citeproc both consume `Cite` nodes. Crossref must run first and consume only its prefixed keys (`fig:`, `eq:`, `tbl:`); citeproc then handles what's left. Reverse the order and citations break.
- **Windows + JSON filters.** Path-shaped pain. Spaces in paths require quoting twice — once for the shell, once for pandoc. Python filters need `--filter "python C:/path with space/filter.py"`. Whenever possible, prefer Lua filters which avoid shell quoting entirely.
- **Lua filter returns wrong type.** A `Header` handler that returns a `pandoc.Str` crashes with `bad argument`. Headers must return `Header`, `Block`, list of `Block`s, or `nil`. Match the type the handler is for.
- **Mutating shared elements.** If a filter modifies `el.content` and another filter caches a reference to the same content table, the second filter sees the mutation. Construct new tables when in doubt.
- **`--filter pandoc-citeproc` is dead.** Use `--citeproc` (built-in since 2.11). The old citeproc binary is no longer shipped.
- **JSON filter spawn cost.** For a single-document conversion this is invisible. For batch processing thousands of files, JSON filters can dominate runtime. Lua filters have ~0 overhead.
- **pandoc-crossref version skew.** pandoc-crossref vN.M.K depends on pandoc API vN.M.K and refuses to run against mismatched pandoc versions. Update both together. The crossref releases page documents which pandoc each release supports.

## Sources

- Pandoc Lua Filters reference (the canonical Lua API doc): https://pandoc.org/lua-filters.html
- Pandoc User's Guide — Filters section: https://pandoc.org/MANUAL.html#filters
- pandoc-crossref repository (install, docs, releases): https://github.com/lierdakil/pandoc-crossref
- pandoc-types Haskell package (the AST definition): https://hackage.haskell.org/package/pandoc-types
- panflute (Python filter library): http://scorreia.com/software/panflute/
- pandocfilters (Python, lighter alternative): https://github.com/jgm/pandocfilters

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
