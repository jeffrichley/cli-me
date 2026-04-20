# Managing ComfyUI custom nodes

ComfyUI loads any subdirectory of `<ComfyUI>/custom_nodes/` as a node pack
on startup. The `custom-nodes` command group manages that directory: clone
new packs from git, list what's installed, pull updates, remove unwanted
packs. ComfyUI does NOT hot-reload custom nodes — every install / update /
remove requires a server restart to take effect.

## Prerequisites

- `COMFY_PATH` env var (or `--path` flag) pointing at the ComfyUI install
  directory — the one containing `custom_nodes/`, `models/`, `main.py`.
  Required for every command in this group.
- `git` on PATH — used for clone / pull / status introspection.
- For `requirements.txt` installs: a Python interpreter that runs ComfyUI.
  Auto-detected in this order:
  1. `--python` flag
  2. `COMFY_PYTHON` env var
  3. `<COMFY_PATH>/python_embeded/python.exe` (Windows portable install)
  4. `<COMFY_PATH>/.venv/{Scripts,bin}/python` (uv-managed venv)
  5. `<COMFY_PATH>/venv/{Scripts,bin}/python` (legacy venv)

  If none are found and the cloned repo has `requirements.txt`, the wrapper
  warns and skips the pip install — install manually with your ComfyUI's
  Python.

## Installing a custom node pack

```bash
# Set this once per shell, then forget about --path
export COMFY_PATH=/path/to/ComfyUI

# Clone + install requirements
uv run comfyui_cli.py custom-nodes install https://github.com/AHEKOT/ComfyUI_VNCCS.git
# → installed: ComfyUI_VNCCS -> /path/to/ComfyUI/custom_nodes/ComfyUI_VNCCS
#   requirements.txt installed
#   restart ComfyUI for the new custom node to load.
```

Verify after restart:

```bash
uv run comfyui_cli.py custom-nodes list
# Shows ComfyUI_VNCCS with its current commit and remote URL.
```

### Install variants

```bash
# Custom directory name (default: derived from URL — strips trailing `.git`
# case-insensitively, trims whitespace from both the URL and the final
# segment, takes the last path segment). Names containing `/`, `\`, or `..`,
# or that are exactly `.` / `..`, are rejected to prevent path traversal.
custom-nodes install https://example.com/myorg/MyNode.git --name MyBar

# Skip pip install (e.g., when you'll manage deps manually)
custom-nodes install https://example.com/myorg/MyNode.git --no-deps

# Force re-clone (deletes the existing directory first — destructive)
custom-nodes install https://example.com/myorg/MyNode.git --force

# Use a specific Python (overrides COMFY_PYTHON / auto-detect)
custom-nodes install https://example.com/myorg/MyNode.git --python /opt/comfy/.venv/bin/python
```

The install is **idempotent by default**: if the target directory already
exists, the command exits 0 with a "skipped" note. Pass `--force` to wipe
and re-clone.

## Listing what's installed

```bash
custom-nodes list                # human-readable Rich table
custom-nodes list --json         # JSON for scripting
```

Each entry includes: name, whether it's a git checkout, current branch + commit,
whether it has `requirements.txt`, and the git remote URL.

## Updating

```bash
# One pack
custom-nodes update ComfyUI_VNCCS

# Every git-tracked pack
custom-nodes update --all

# Update without reinstalling requirements (faster when you know they're stable)
custom-nodes update ComfyUI_VNCCS --no-deps
```

`update` runs `git pull --ff-only` (refuses to merge — fails clearly if upstream
diverged from the local). When the pull actually advances HEAD AND the repo has
`requirements.txt`, the wrapper reinstalls dependencies automatically. If the
pull is "Already up to date", pip install is skipped.

In `--all` mode, per-pack failures don't abort the run — each failure is recorded
and the next pack continues.

## Removing

```bash
custom-nodes remove ComfyUI_VNCCS --yes
```

`--yes` is required (no implicit confirmation). Names containing `/`, `\`, or
`..`, or that are exactly `.` / `..`, are rejected to prevent accidental
escapes from `custom_nodes/`. If the target is a **symlink**, remove refuses
rather than following it — a symlinked custom node pointing outside
`custom_nodes/` would otherwise have its contents recursively deleted.
Remove the symlink manually (`rm` / `del`) if you're sure. The delete handles
read-only files (notably `.git/objects/` on Windows and any files chmod'd
read-only on POSIX) automatically.

## Restart ComfyUI

ComfyUI scans `custom_nodes/` once at startup. After install / update / remove,
restart the server (Ctrl-C the running process and re-run your `python main.py`
or service unit). The wrapper prints a `restart ComfyUI` reminder after each
mutating operation so it's hard to forget.

## Common gotchas

- **`requirements.txt` installed in the wrong Python** — the most common
  custom-node failure mode. If your ComfyUI runs in a portable embed
  (`python_embeded/`) but you let pip install into your system Python,
  the node will import-fail at startup. Set `COMFY_PYTHON` once and forget it.
- **Submodules** — `--depth 1` clone skips submodules. If a node needs them,
  `cd` into the directory and run `git submodule update --init` manually.
- **Diverged local changes block update** — `git pull --ff-only` refuses to
  merge. If you've patched a custom node locally, either commit + rebase
  manually, or `custom-nodes remove` and `custom-nodes install --force`.
- **Custom node with no `__init__.py`** — ComfyUI silently skips it. Check
  the cloned directory contains a Python entry point.

## Sources

- ComfyUI custom node loading docs: https://docs.comfy.org/custom-nodes/overview
- ComfyUI Manager (the in-app equivalent): https://github.com/Comfy-Org/ComfyUI-Manager
- Git for Windows read-only cleanup pattern: https://docs.python.org/3/library/shutil.html#rmtree-example

## Learned from Usage

(Append entries here as agents discover footguns or improvements.)
