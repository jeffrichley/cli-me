# Key Functions

Source-level entry points the CLI wrapper for pandoc 3.9.0.2 (commit c15e062) will rely on, organized by MVP command group. The wrapper invokes pandoc as a subprocess — these are the Haskell functions that handle the corresponding flags inside the binary, useful for understanding what each flag actually does and where to look when debugging.

All paths are relative to `E:/workspaces/tools/cli-me/tmp/source-analysis/pandoc/`.

## Argument parsing & dispatch

### `parseOptions` — `src/Text/Pandoc/App/CommandLineOptions.hs:69`

Top-level CLI parser. Reads `getArgs`, runs `parseOptionsFromArgs`, returns either an `Opt` (the populated options record) or an `OptInfo` (a print-and-exit request like `--list-input-formats`).

### `options` — `src/Text/Pandoc/App/CommandLineOptions.hs:272`

The `[OptDescr]` list that defines every CLI flag. ~150 entries, one per flag. Each entry maps a flag to a state-update function on `Opt`. This is the canonical inventory.

### `convertWithOpts` — `src/Text/Pandoc/App.hs:295`

Orchestrator: takes a fully-populated `Opt`, runs the read → transforms → filters → write pipeline. Single line at 303 chains the filter step:

```
... >=> applyFilters scriptingEngine filterEnv filters [T.unpack format] >=> ...
```

### `handleOptInfo` — `src/Text/Pandoc/App/CommandLineOptions.hs:111`

Handles the print-and-exit branches: `--version`, `--help`, `--list-*`, `--print-default-template`, `--bash-completion`. Useful for the wrapper's `info` group.

## convert (md ↔ {pdf, docx, html, epub, latex})

### `getReader` — `src/Text/Pandoc/Readers.hs:192`

Lookup function: takes a `FlavoredFormat` (format name plus extension diff like `markdown+yaml_metadata_block`) and returns the matching `Reader` plus the resolved `Extensions` set. Throws `PandocUnknownReaderError` for unknown formats.

### `readers` — `src/Text/Pandoc/Readers.hs:137`

The `[(Text, Reader m)]` table. Each entry maps a format name to a `TextReader` or `ByteStringReader`. Adding/removing input formats happens here.

### `getWriter` — `src/Text/Pandoc/Writers.hs:235`

Mirrors `getReader` for the output side. Returns `(Writer, Extensions)`.

### `writers` — `src/Text/Pandoc/Writers.hs:156`

The writer table. ~64 entries.

### `makePDF` — `src/Text/Pandoc/PDF.hs:76`

Generates PDF by writing the document in an intermediate format (LaTeX, HTML, ConTeXt, ms, or Typst) and shelling out to a `--pdf-engine`. Picks the intermediate format based on which engine the user specified. There is no direct `pdf` writer in the writers table.

### `optToOutputSettings` — `src/Text/Pandoc/App/OutputSettings.hs`

Resolves the output writer from the `--to` flag (or infers from the output filename extension). Resolves template, reference-doc, syntax-highlighting style, and other writer-specific settings into a `WriterOptions` record.

## citations (--bibliography, --csl, --citeproc)

### `processCitations` — `src/Text/Pandoc/Citeproc.hs:8`

Single entry point for citeproc. Walks the `Pandoc` AST, finds all `Cite` nodes, resolves them against the loaded bibliography and CSL style, and returns a modified `Pandoc` with formatted citations and an appended bibliography section.

### `readBibtexString` — `src/Text/Pandoc/Citeproc/BibTeX.hs`

Parses BibTeX/BibLaTeX into `Citeproc.Reference` values. Imported into `Citeproc.hs:18`.

### `cslJsonToReferences` — `src/Text/Pandoc/Citeproc/CslJson.hs`

Parses CSL JSON. Imported into `Citeproc.hs:17`.

### `parseLocator` — `src/Text/Pandoc/Citeproc/Locator.hs`

Parses citation locators like `[@smith2020, p. 23-25]`. Imported into `Citeproc.hs:15`.

The `--citeproc` (`-C`) flag adds `CiteprocFilter` to the filter list (App/CommandLineOptions.hs:1000). `--bibliography FILE` appends to `optMetadata` under the `bibliography` key (line 1006-1014). `--csl FILE` writes to `optMetadata` key `csl` (line 1015-1024).

## templates (--template, --reference-doc, --include-*)

### `compileTemplate` — re-exported in `src/Text/Pandoc/Templates.hs:36`

From the doctemplates library. Compiles a template source string into a `Template` value. Pandoc wraps this so partials are resolved against the data dir.

### `renderTemplate` — re-exported in `src/Text/Pandoc/Templates.hs:36`

Renders a compiled `Template` against a `Context` (variable bindings).

### Default-template loader — `src/Text/Pandoc/Templates.hs:141`

```haskell
compileTemplate ("templates/default." <> T.unpack writer) ...
```

This is what `--template`-less invocations end up calling when `--standalone` is set.

### `--reference-doc FILE` handling — `src/Text/Pandoc/App/CommandLineOptions.hs:628`

Stores the path on `Opt` as `optReferenceDoc`. The docx/odt/pptx writers in `src/Text/Pandoc/Writers/Docx.hs`, `Writers/ODT.hs`, `Writers/Powerpoint.hs` read this and copy styles from the file at write-time.

### `--include-in-header`, `-before-body`, `-after-body` — App/CommandLineOptions.hs:498, 506, 514

Each appends to a list on `Opt`. Files are read at write-time and injected as raw blocks into the corresponding template variables (`header-includes`, `include-before`, `include-after`).

## filters (--lua-filter, --filter)

### `applyFilters` — `src/Text/Pandoc/Filter.hs:76`

Folds the supplied `[Filter]` list left-to-right, dispatching each to the JSON filter runner, the Lua engine, or `processCitations` based on filter type.

### `applyFilter` (inner) — `src/Text/Pandoc/Filter.hs:87-92`

The dispatch:
- `JSONFilter f` → `JSONFilter.apply fenv args f doc`
- `LuaFilter f` → `engineApplyFilter scrngin fenv args f doc`
- `CiteprocFilter` → `processCitations doc`

### `expandFilterPath` — `src/Text/Pandoc/Filter.hs:104`

Resolves filter paths against the data dir (so a filter installed in `~/.local/share/pandoc/filters/foo.lua` can be referenced as just `foo.lua`).

### `JSONFilter.apply` — `src/Text/Pandoc/Filter/JSON.hs`

Runs the external program with the AST as JSON on stdin and the output format as `argv[1]`. Reads the modified AST from stdout.

### `runFilterFile` — `pandoc-lua-engine/src/Text/Pandoc/Lua/Filter.hs:26`

Loads a Lua filter file, executes it in the global Lua environment, and applies whatever filters it returns (or the implicit globals) to the document.

### `runFilterFile'` — `pandoc-lua-engine/src/Text/Pandoc/Lua/Filter.hs:33`

Same as `runFilterFile` but with a custom environment table — used by the engine to provide the `pandoc.*` namespace as locals.

### `engineApplyFilter` — `pandoc-lua-engine/src/Text/Pandoc/Lua/Engine.hs`

The bridge between `applyFilters` and the Lua engine. Wraps the `LuaE` monad in `IO`.

## info (--list-*, --version)

All in `src/Text/Pandoc/App/CommandLineOptions.hs`:

| Flag | Line | Function |
|---|---|---|
| `--list-input-formats` | 1135 | Iterates `readers` and prints names |
| `--list-output-formats` | 1139 | Iterates `writers` and prints names |
| `--list-extensions[=FORMAT]` | 1143 | Prints `Extensions` for FORMAT (or all known extension flags if FORMAT omitted) |
| `--list-highlight-languages` | 1148 | From `Skylighting.defaultSyntaxMap` |
| `--list-highlight-styles` | 1152 | From `Text.Pandoc.Highlighting.highlightingStyles` |
| `--print-default-template` | 1156 | Calls `getDefaultTemplate` for FORMAT |
| `--print-default-data-file` | 1163 | Calls `readDefaultDataFile` for FILE |
| `--print-highlight-style` | 1170 | Serializes a Skylighting `Style` as KDE XML |
| `--version` | 1178 | Calls `versionInfo` (line 1299) |
| `--help` | 1182 | Prints `usageInfo` over the `options` list |

### `versionInfo` — `src/Text/Pandoc/App/CommandLineOptions.hs:1299`

Builds the `--version` output: pandoc version, scripting engine, features list, user data dir path, copyright. Inputs come from cabal flags (`flag lua`, `flag server`) at compile time.

## Defaults file machinery

### `applyDefaults` — `src/Text/Pandoc/App/Opt.hs` (re-exported via `import Text.Pandoc.App.Opt` in CommandLineOptions.hs:53)

Merges a YAML defaults file into `Opt`. Called when `--defaults FILE` (`-d`) is processed at CommandLineOptions.hs:316-330.

### `fullDefaultsPath` — `src/Text/Pandoc/App/Opt.hs`

Resolves a defaults file path against the user data dir (so `-d article` finds `~/.local/share/pandoc/defaults/article.yaml`).

## Sandbox

### `sandbox'` — `src/Text/Pandoc/App/OutputSettings.hs`

Wraps the IO action so file-system access is restricted to the explicit input/output files when `--sandbox` is set. Useful context for the wrapper if it needs to expose `--sandbox` for safety.

## Sources

- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\App.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\App\CommandLineOptions.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\App\Opt.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\App\OutputSettings.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Readers.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Writers.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Filter.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Filter\JSON.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Citeproc.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\Templates.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\src\Text\Pandoc\PDF.hs`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pandoc\pandoc-lua-engine\src\Text\Pandoc\Lua\Filter.hs`
- https://github.com/jgm/pandoc/tree/main/src/Text/Pandoc
- https://github.com/jgm/pandoc/tree/main/pandoc-lua-engine
