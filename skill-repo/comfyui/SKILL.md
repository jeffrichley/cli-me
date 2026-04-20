---
name: comfyui
description: ComfyUI generation CLI — submit workflows, track progress, download outputs, manage models/inputs. Use when asked to "generate image with ComfyUI", "run a ComfyUI workflow", "queue a ComfyUI prompt", "submit a workflow", "use ComfyUI", "ComfyUI text-to-image", "ComfyUI img2img", "ComfyUI inpaint", "ComfyUI upscale", "SDXL / Flux / SD3 via ComfyUI", "extract workflow from image", "list ComfyUI checkpoints/loras", or anything involving `http://127.0.0.1:8188`.
---

# comfyui — cli-me skill

Intent-based CLI for ComfyUI. This skill talks to a running ComfyUI server
via its HTTP and WebSocket APIs — it does not run ComfyUI itself.

> **ComfyUI vs other image tools:** ComfyUI is a node-graph workflow engine.
> Workflows come in two formats: UI (the in-app graph) and API (flat
> `{node_id: {class_type, inputs}}`). This CLI accepts both for `workflow run`
> but the raw `/prompt` endpoint only accepts API format.

## Prerequisites

- ComfyUI must be running and reachable at `http://127.0.0.1:8188`
  - Override via `COMFY_URL` env var or per-command `--url` flag
  - Start ComfyUI: see https://github.com/comfyanonymous/ComfyUI#installation
- Python 3.12+
- uv (Python package runner): https://docs.astral.sh/uv/getting-started/installation/

## CLI Commands

Run commands from the skill's `scripts/` directory:
```bash
cd <skill-dir>/scripts
uv run comfyui_cli.py <group> <command> [options]
```

Or from any directory using the full path:
```bash
uv run --project <skill-dir>/scripts <skill-dir>/scripts/comfyui_cli.py <group> <command> [options]
```

To discover available flags for any command:
```bash
uv run comfyui_cli.py <group> <command> --help
```

### Command Groups

| Group | Purpose |
|-------|---------|
| `server` | Probe ComfyUI availability and print system info |
| `queue` | Submit prompts, track status, cancel/clear, free memory |
| `workflow` | Run/validate/extract/parameterize workflow JSON |
| `model` | List and find checkpoint/LoRA/VAE/etc. model files |
| `input` | Upload and list input images |
| `output` | Download and inspect workflow outputs |
| `custom-nodes` | Install/list/update/remove ComfyUI custom node packs (git-based) |

### Commands

**server**
- `server ping` — GET `/system_stats`; prints `ok` on success, `fail` on error
- `server info [--json]` — pretty-print `/system_stats` as a table (default) or raw JSON

**queue**
- `queue submit FILE [--client-id ID]` — POST `/prompt`; prints `prompt_id`
- `queue status [PROMPT_ID]` — show status for a prompt, or overall queue depth
- `queue list` — GET `/queue` as a human-readable table
- `queue wait PROMPT_ID [--live] [--timeout N]` — poll `/history` or stream `/ws` progress
- `queue cancel PROMPT_ID` — targeted `/interrupt` + `/queue` delete
- `queue clear` — clear the entire queue
- `queue free [--unload-models] [--free-memory]` — POST `/free`

**workflow**
- `workflow run FILE [--live] [--output-dir DIR]` — submit + wait + download outputs (auto-detects JSON/PNG/WebP)
- `workflow set IN.json [--param KEY=VAL ...] [-o OUT.json]` — substitute parameters (`NODE_ID.key`, `@Title.key`, `class:Class.key`, `seed=random`)
- `workflow validate FILE` — detect UI vs API; check class_types and link targets
- `workflow extract IMAGE.png [--ui | --api | --both] [-o OUT]` — pull embedded workflow from PNG/WebP

**model**
- `model list [--type TYPE]` — list model files for `checkpoints`/`loras`/`vae`/`text_encoders`/`controlnet`/`upscale_models`/...
- `model find NAME` — case-insensitive search across all types

**input / output**
- `input upload FILE [--subfolder X] [--overwrite]` — POST `/upload/image`, prints `{name, subfolder, type}`
- `input list [--subfolder X] [--local]` — requires `--local` (ComfyUI exposes no listing endpoint)
- `output download PROMPT_ID [--dir DIR]` — resolve `/history` then GET `/view` per image
- `output show PROMPT_ID` — JSON dump of the outputs section

**custom-nodes**
- `custom-nodes install REPO_URL [--name N] [--path P] [--python P] [--no-deps] [--force]` — git clone into `<ComfyUI>/custom_nodes/`, optionally `pip install -r requirements.txt`
- `custom-nodes list [--path P] [--json]` — enumerate installed packs with git ref + remote
- `custom-nodes update [NAME|--all] [--path P] [--python P] [--no-deps]` — `git pull --ff-only` + reinstall reqs (when changed)
- `custom-nodes remove NAME [--path P] --yes` — delete the directory (requires explicit `--yes`)

  Requires `COMFY_PATH` env var or `--path` flag pointing at the ComfyUI install directory (the one containing `custom_nodes/`). For `requirements.txt` installs, the wrapper auto-detects ComfyUI's Python at `python_embeded/`, `.venv/`, or `venv/`; override with `--python` or `COMFY_PYTHON` env. ComfyUI must be **restarted** after install/update/remove for changes to take effect (no hot-reload).

### Default Behavior

- **Base URL:** `http://127.0.0.1:8188`, overridable via `COMFY_URL` env or `--url` flag.
- **Origin header:** the CLI sets `Origin: <base_url>` on every request to satisfy ComfyUI's origin-guard (see `references/gotchas.md`).
- **Outputs download to the current working directory** unless `--output-dir` is specified.
- **Exit codes:** `2` = connection/origin error, `3` = validation error (bad workflow), `4` = execution error, `5` = output not found, `6` = ComfyUI install path missing/invalid (custom-nodes group), `7` = git/pip subprocess failure (custom-nodes group).

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how a command works under the hood, check the
relevant technique page — it explains the endpoint contracts, event shapes,
and failure modes.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

**Important:** Always read an existing page before modifying it. Do not create
new pages that duplicate existing topics — update the existing page instead.

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Append a timestamped entry to `references/log.md` with what you did and
   what you learned
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
