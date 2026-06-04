---
name: gimp
description: Agent-native CLI for GIMP batch automation — run Script-Fu or Python batch expressions headlessly, inspect installed version/capabilities, and execute repeatable non-interactive image workflows. Use when asked to "batch edit images", "run gimp from command line", "script-fu batch", "python-fu batch", "headless gimp", "automate gimp", or "process images without opening GUI".
---

# GIMP - cli-me skill

CLI-powered interface for GIMP. This skill wraps the real GIMP executable - it does
not reimplement image editing functionality in Python.

## Prerequisites

- GIMP must be installed:
  - Windows: `winget install GIMP.GIMP`
  - macOS: `brew install --cask gimp`
  - Linux: `apt install gimp` (or distro equivalent)
- Python 3.12+
- `uv` CLI for running the local skill environment (`pip install uv` if missing)

## CLI Commands

From `skill-repo/gimp/`, run commands via:

```bash
uv run scripts/gimp_cli.py <command> [options]
```

### Available Commands

- `info version` - show installed GIMP version
- `info capabilities` - show discovered binary path and key batch flags
- `batch run` - execute one or more `--batch` expressions with safe headless defaults
- `pod resize` - resize artwork to exact POD pixel dimensions
- `pod fit-crop` - scale-to-fill and crop to product aspect ratio
- `pod prep` - one-shot prep (scale + DPI metadata + export)

## Default Behavior

- Default binary probe order: `gimp-console-3.0`, `gimp-console-2.10`, `gimp-console`,
  `gimp-3.0`, `gimp-2.10`, `gimp`, then common Windows install paths.
- `batch run` defaults to non-interactive automation flags:
  - `--new-instance --no-interface --console-messages --no-splash`
- `batch run` and `pod` commands auto-quit by default to avoid lingering processes.
  On GIMP 2.10, this uses an explicit `(gimp-quit 0)` batch expression because
  `--quit` is not supported.
- Overwrite prompts are not applicable in this wrapper because writes are handled
  inside user-supplied batch expressions; keep expressions non-interactive.
- Processing time depends on script complexity. Use longer shell timeouts for heavy
  jobs (for example `timeout: 600000` for long pipelines).

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how something works under the hood, check
`references/source-analysis/`.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Log what you did: `clime log append --skill <name> --message "<what you did and learned>" --log-file references/log.md`
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
