# pandoc Gotchas

Known issues, workarounds, and things that will bite you. All verified against
pandoc 3.9.0.2 at the time of writing.

## PDF Engines Are Separate Installs

Pandoc has no native PDF writer. `-t pdf` (or `-o foo.pdf`) shells out to an
external engine: `pdflatex`, `xelatex`, `lualatex`, `weasyprint`, `wkhtmltopdf`,
`prince`, `pagedjs-cli`, or `tectonic`. Each must be installed and on `PATH`
separately. If the chosen engine is missing, pandoc errors at runtime with:

```
Argument of --pdf-engine must be one of
    weasyprint
    wkhtmltopdf
    pagedjs-cli
    prince
```

(The list shows engines actually found on `PATH`, not the full set pandoc supports.)

For Markdown → PDF on this Windows machine, MiKTeX provides `pdflatex` /
`xelatex`. Default engine is `pdflatex` for `-t pdf`; `weasyprint` for
HTML-to-PDF flows.

## `--self-contained` Is Deprecated

Use `--embed-resources --standalone` instead. The old flag still works but
prints `[WARNING] Deprecated: --self-contained. use --embed-resources --standalone`.

## `--standalone` Is Implicit

When you pass `--template`, `--self-contained`/`--embed-resources`, or any
`--include-*` flag, pandoc auto-enables `--standalone`. Don't double-emit it;
it's harmless but noisy.

## `--reference-doc` Silently Ignored Outside DOCX/ODT/PPTX

If you pass `--reference-doc=ref.docx -t html`, pandoc returns exit 0 with no
warning and no log line — the flag is silently ignored. The wrapper should
validate that the output format is one of {docx, odt, pptx} when this flag is
present, or the user will be confused why their styling doesn't apply.

## Filter Ordering Is CLI Order

`--filter`, `--lua-filter`, and `--citeproc` all execute as filters in the
order they appear on the command line. If `--citeproc` runs before a filter
that adds citations to the AST, the new citations won't be processed.
Convention: put `--citeproc` LAST unless you have a specific reason.

## `--natbib` and `--biblatex` vs `--citeproc`

These three flags are conceptually mutually exclusive — they're three different
ways to handle citations. Pandoc accepts the combination silently (no error,
no warning), and the last one specified takes effect. Don't combine them.
Treat them as exclusive; the wrapper should reject the combo.

## Bibliography Format Auto-Detection

`--bibliography` auto-detects format by file extension: `.bib`, `.bibtex`,
`.json` (CSL-JSON), `.yaml` (CSL-YAML), `.ris`. **`.enl` is binary EndNote and
is NOT a bibliography format** — pandoc errors with "Could not determine
bibliography format". For EndNote XML data, convert to BibTeX or CSL-JSON
first (Zotero with the Better BibTeX extension is the easiest path).

## Multi-Source Metadata: "Later Wins"

When multiple metadata sources set the same key, **later wins**:
- Multiple input documents (`pandoc a.md b.md`): `b.md`'s metadata overrides `a.md`'s
- Multiple `--metadata-file` flags: the last one wins
- This is verified runtime behavior on 3.9.0.2

## Metadata Priority Order

For a single key set by multiple sources, the priority is (highest first):
- `-M` / `--metadata` from the CLI
- YAML frontmatter in the document
- `--metadata-file FILE`

Don't trust intuition that "deeper = more specific = wins." The CLI has the
final say over frontmatter, but `--metadata-file` is the lowest layer.

## `-V toc=false` Doesn't Disable TOC

`-V` writes to the **template variable** namespace (which templates consult)
not the metadata namespace. Templates check truthiness with `$if(toc)$ ... $endif$`,
and the string `"false"` is truthy in pandoc templates. Use `--metadata toc=false`
or just omit the flag instead.

## Lua Filter Type Matching

Lua filter handler functions must return the right node type:
- `Header(el)` returns a `Block` (Header is a Block element) — use `pandoc.walk_block` if you walk into it
- `Image(el)` returns an `Inline` (or list of Inlines) — `pandoc.Span` is fine; `pandoc.Div` is a Block and will error with `object has no __toinline metamethod`
- `Figure(el)` returns a `Block` — `pandoc.Div` is fine here

Mismatched types fail with cryptic `__toinline` / `__toblock` metamethod errors.

## Lua Engine Is Lua 5.4

Pandoc 3.9.0.2 ships Lua 5.4. Filters written for older Lua versions
(`pandoc.utils.stringify` semantics, table iteration) generally work but
double-check version-specific behavior in long-lived filter code.

## pandoc-crossref Version-Locked

`pandoc-crossref` releases are tied to specific pandoc versions. Using a
mismatched pair causes either silent reference failures or hard errors.
The skill wrapper verifies presence but does NOT auto-install — agents
should read `gotchas.md#pandoc-crossref-installation` for the install matrix.

## pandoc-crossref Installation

Not bundled. Install separately:
- Binary: https://github.com/lierdakil/pandoc-crossref/releases (match version to your pandoc 3.9.x)
- `cabal install pandoc-crossref` (requires Haskell toolchain)
- `choco install pandoc-crossref` (Windows package manager)
- `brew install pandoc-crossref` (macOS)

The wrapper checks `which pandoc-crossref` before invoking filter commands
that need it, and emits an install hint if missing.

## Windows: File Locking on Output

If you have an output `.docx` open in Microsoft Word, pandoc's write fails
with a permission error. Close the file in Word before re-running.

## Windows: `--resource-path` Separator

Use `;` (semicolon) on Windows, `:` (colon) on POSIX. Pandoc respects platform
conventions.

## Windows: Path Separators in Defaults Files

In YAML defaults files, prefer forward slashes (`C:/path/to/refs.bib`) —
backslashes need escaping (`C:\\path\\to\\refs.bib`). Forward slashes are
portable and cleaner.

## Windows: JSON Filter Quoting

External JSON filters (programs invoked via `--filter`) suffer Windows shell
quoting pain. Prefer Lua filters when possible — they're in-process and avoid
the subprocess argv translation. If you must use a Python JSON filter, wrap it
in a `.cmd` shim or invoke via `--filter "py -3 figcount.py"`.

## No Interactive Prompts

Pandoc has no interactive prompts. Agents won't hang waiting for stdin.
However, pandoc DOES read from stdin if no input file is given — if the
wrapper accidentally calls pandoc without a file argument, it'll silently
block waiting for stdin EOF.

## Extension Syntax: `+ext-ext`

Format extensions use `+` to enable, `-` to disable, e.g.,
`markdown+yaml_metadata_block-implicit_figures`. List extensions per format
with `pandoc --list-extensions=markdown` (substitute the format you care about).

## `--top-level-division=default` Is Undocumented

`--help` lists only `section|chapter|part`, but the binary accepts `default`
without error. Behavior is undocumented; stick to the three documented values
in code that needs to be predictable.
