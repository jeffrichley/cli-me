---
name: comfyui-vnccs
description: Visual novel character sprite pipeline for ComfyUI — generate consistent character sheets, clothing sets, emotions, and final sprites via ComfyUI_VNCCS custom nodes. Use when asked to "create a VN character", "generate a character sheet", "add clothing to a character", "generate emotions", "render sprites", "build a VN character", "create consistent character sprites", "export a character LoRA dataset", or for any visual-novel / anime-character asset pipeline on top of ComfyUI.
---

# comfyui-vnccs — cli-me skill

Agent-native wrapper for the [ComfyUI_VNCCS](https://github.com/AHEKOT/ComfyUI_VNCCS) (Visual Novel Character Creation Suite) ComfyUI custom node pack. Orchestrates a 5-stage pipeline for generating consistent character sprites: **character sheet → clothing sets → emotions → sprites → (optional) LoRA dataset**.

This skill composes on top of the sibling `comfyui` cli-me skill — it loads bundled VNCCS workflow JSONs, patches parameters into them, and hands off to `comfyui` for submission + output retrieval. **No image generation happens in this skill itself** — ComfyUI does all the heavy lifting.

## Prerequisites

- **ComfyUI running** and reachable at `http://127.0.0.1:8188` (override with `COMFY_URL` env var). Start ComfyUI from `<COMFY_PATH>/main.py`.
- **`COMFY_PATH` env var** set to your ComfyUI install directory (e.g. `E:/workspaces/tools/comfy/ComfyUI`). Required so the wrapper can read VNCCS's state (character sheets, costumes, emotions) off the filesystem and enumerate them for `list` / `show` commands.
- **Installed custom node packs** (use the sibling `comfyui custom-nodes install` to set these up):
  - `ComfyUI_VNCCS` — the core pack (version 2.1.0 or later)
  - `ComfyUI-Impact-Pack` — provides `UltralyticsDetectorProvider`, `FaceDetailer`
  - `ComfyUI-GGUF` — provides `UnetLoaderGGUF` (for QWEN UNet loading)
  - `ComfyUI-SeedVR2_VideoUpscaler` — provides the upscaler subgraphs
  - `ComfyUI-Easy-Use` — provides `easy cleanGpuUsed`
  - `comfyui_controlnet_aux` — provides preprocessor nodes
  - `was-node-suite-comfyui` — provides `Save Text File` (stage 5)
  - `ComfyUI_UltimateSDUpscale` — provides `UltimateSDUpscale`
  - `rgthree-comfy` — provides utility/layout nodes
- **Models** — see `references/source-analysis/required-models.md` for the 16 required model files (including the SeedVR2 DiT + VAE pair) plus 1 optional RMBG variant. Three additional RMBG variants (INSPYRENET, BEN, BEN2) are auto-downloaded lazily by VNCCS's RMBG2 node at first use and don't need pre-fetching. Run `vnccs check models` to see what's missing. Full install footprint: **~28-46 GB**.
- **Python 3.12+**

Verify setup (run from the skill's `scripts/` directory):
```bash
cd skill-repo/comfyui-vnccs/scripts
uv run vnccs_cli.py check all
```

## CLI Commands

Run from the skill's `scripts/` directory:
```bash
cd skill-repo/comfyui-vnccs/scripts
uv run vnccs_cli.py <group> <command> [options]
```

### Command Groups (8)

| Group | Purpose |
|---|---|
| `check` | Verify VNCCS + custom nodes + models are installed |
| `character` | Create, clone, list, inspect, prune characters |
| `clothing` | Add / remove / list / pick clothing variants per character |
| `emotion` | Add / list / show / preview emotion sheets per costume |
| `sprite` | Render final sprites (combines character + costume + emotion) |
| `dataset` | Export LoRA training datasets from generated sprites |
| `pose` | List built-in pose presets |
| `config` | Show VNCCS configuration |

### Commands

**check** — status and dependency verification
- `check nodes` — verify every required custom-node pack is installed in ComfyUI
- `check models` — verify every required model file is present; emit download hints for missing
- `check all` — runs nodes + models + server-reachable checks

**character** — stage 1 + 1.1
- `character create NAME --description "..." [--pose NAME] [--seed N]` — generate character sheet from prompt
- `character clone NAME --from EXISTING [--prompt "..."]` — derive variant from existing character (stage 1.1)
- `character list` — enumerate saved characters
- `character show NAME` — inspect a character's details + generated artifacts
- `character prune NAME --yes` — delete a character's artifacts (character sheet + costumes + emotions)

**clothing** — stage 2
- `clothing add CHARACTER --name COSTUME --description "..." [--variants N] [--seed N]`
- `clothing list [CHARACTER]` — enumerate costume sets
- `clothing remove CHARACTER --name COSTUME --yes`
- `clothing pick CHARACTER --name COSTUME --variant N` — select one of N generated variants as the final costume

**emotion** — stage 3
- `emotion add CHARACTER --emotion TYPE [--costume NAME] [--legacy | --qwen] [--denoise FLOAT] [--seed N]` — generate emotion sheet. **Default: `--legacy`** (uses the stable SDXL workflow). `--qwen` opts into the upstream VNCCS 2.1.0 QWEN path which is currently broken (missing `VNCCS_QWEN_Detailer` / `VNCCS_BBox_Extractor` nodes in the published pack). See `references/gotchas.md`.
- `emotion list CHARACTER` — enumerate emotion types per costume
- `emotion show CHARACTER --emotion TYPE [--costume NAME]` — inspect details
- `emotion preview CHARACTER --emotion TYPE` — preview a pre-rendered emotion sample

**sprite** — stage 4
- `sprite render CHARACTER [--seed N]` — render final VN-ready sprites for every costume × emotion combination for this character. **No filtering** — renders everything on disk. Slow: minutes per sprite on GPU.

**dataset** — stage 5
- `dataset export CHARACTER --out PATH [--game-name STR]` — package generated sprites into a LoRA training dataset (images + captions)
- `dataset preview CHARACTER` — show what the export WOULD produce without creating files

**pose**
- `pose list` — enumerate bundled pose presets (from VNCCS's `presets/poses/`)

**config**
- `config show` — print the resolved `COMFY_PATH`, `COMFY_URL`, VNCCS install path, and workflow bundle location

### Default Behavior

- **Emotion workflow defaults to `--legacy`** (SDXL) because VNCCS 2.1.0's QWEN emotion workflow references two unregistered node classes (upstream bug, tracked in `gotchas.md`). Switch to `--qwen` when upstream publishes the fix.
- **Sprite render has no per-costume filter** — it renders everything the character has on disk, as per VNCCS's sprite_generator node design.
- **Workflow submission** delegates to ComfyUI's `/prompt` endpoint. UI → API format conversion is handled by the sibling `comfyui` skill's `workflow run` logic.
- **Timeouts:** character creation ~30-60s on GPU, clothing ~60-90s per variant, emotion sheets ~30-60s per type, sprite render ~2-5 min per character (many sub-generations). Use `timeout: 600000` minimum for most commands.
- **Exit codes:**
  - `2` — ComfyUI not reachable (server down / wrong URL)
  - `3` — workflow or command input validation failed before submission (mutex flags, unknown emotion type, etc.)
  - `4` — ComfyUI execution error during workflow run
  - `5` — resource not found: character / costume / emotion **or** missing dependency detected by `check` commands (e.g., required model file absent). The `check` commands distinguish the two in their output text; programmatic callers should parse both.
  - `6` — `COMFY_PATH` missing or doesn't look like a ComfyUI install
  - `7` — bundled workflow JSON missing or corrupt

## Knowledge Base

Start with `references/index.md` — that's the table of contents.

- **`references/source-analysis/`** — deep documentation of VNCCS's 22 node classes, 6 workflow JSONs, state management conventions, required models
- **`references/techniques/`** — how-to pages for each pipeline stage
- **`references/gotchas.md`** — the upstream bugs and workarounds (especially Stage 3)
- **`references/future-scope.md`** — what's deferred

## After Completing Your Task

Before ending, update the knowledge base:

1. If you discovered a technique that worked well, update the relevant `references/techniques/` page
2. Document new failure modes in `references/gotchas.md`
3. Log what you did + learned in `references/log.md`
4. Update `references/index.md` if you added new pages
5. Include source URLs for external knowledge
