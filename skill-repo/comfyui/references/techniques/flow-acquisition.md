---
title: ComfyUI Workflow Acquisition
description: Where to find ComfyUI workflows, how to extract them from images, and how to resolve their dependency chain (models + custom nodes) before running.
---

# ComfyUI Workflow Acquisition

An agent asked to "generate a cinematic product shot" or "run an img2img pipeline with depth controlnet" shouldn't hand-roll the workflow JSON. Thousands of existing workflows exist online, most of them higher-quality than anything a model would write from scratch. This page covers **where to find them, how to extract them, and how to resolve their dependencies** (missing models, missing custom nodes) before running.

For workflow format details see [workflow-formats.md](workflow-formats.md); for acquiring the models a workflow needs see [model-acquisition.md](model-acquisition.md); this page focuses on finding and preparing the *workflow JSON* itself.

## 1. Sources

### Canonical examples (always start here)

- **`comfyanonymous/ComfyUI_examples` repo** — <https://github.com/comfyanonymous/ComfyUI_examples> — the upstream gallery of reference workflows maintained by ComfyUI's main author. Browse at <https://comfyanonymous.github.io/ComfyUI_examples/>. Every example page includes a generated PNG you can drag into the UI OR pipe to `workflow extract`.
- **`Comfy-Org/workflow_templates`** — <https://github.com/Comfy-Org/workflow_templates> — official template catalog. Same repo the ComfyUI frontend uses for its "Browse Templates" panel. Covers SDXL, Flux, SD3.5, HunyuanVideo, WAN, etc.
- **`script_examples/` in the ComfyUI source tree** (on this install: `E:\workspaces\tools\comfy\ComfyUI\script_examples\`) — canonical examples of the HTTP + WS API-format workflow. `basic_api_example.py` is the minimal SD 1.5 workflow; `websockets_api_example.py` shows the /ws + /history pattern. These are Python files that BUILD a workflow dict — use them as reference shapes.

Download a canonical example:

```bash
# Latest commit, "flux schnell" example
curl -L -o flux_schnell_example.png \
  "https://comfyanonymous.github.io/ComfyUI_examples/flux/flux_schnell_example.png"
comfyui-cli workflow extract flux_schnell_example.png > flux_schnell_api.json
comfyui-cli workflow validate flux_schnell_api.json
```

### Community workflow hubs

- **OpenArt.ai workflow browser** — <https://openart.ai/workflows/home> — filterable by base model (SDXL, Flux, SD3), use case (character, product, upscale), license. Each workflow has a "Download" button that emits a `.json` (usually API format, some are UI format — always `workflow validate` first). A large fraction are PNG-embedded so `workflow extract` works.
- **Civitai workflows** — <https://civitai.com/models?tag=workflow> — filter the main model browser to `type=Workflows`. Each posting attaches either a `.json` or a PNG-with-embedded-workflow. Civitai workflows are usually tied to specific community checkpoints, so expect a `model-acquisition` round-trip after download.
- **r/comfyui on Reddit** — PNG drops are the dominant format. Save the image, run `comfyui workflow extract IMAGE.png`. The community convention is "post the image, people drag it in" — this only works because ComfyUI embeds the `prompt` chunk in every PNG by default (see [workflow-formats.md](workflow-formats.md)).
- **HuggingFace "ComfyUI" tag** — model repos sometimes ship example workflows in their README or a `workflows/` subdirectory. Look at <https://huggingface.co/models?other=comfyui> for a filter, or check an individual model page's "Files" tab.

### Per-model examples

For any model you download, its HF/Civitai page usually links a reference workflow. Flux, SD3.5, WAN, Hunyuan all have official reference flows maintained by their respective labs — the Comfy-Org repacks in particular ship a companion template in `Comfy-Org/workflow_templates`.

## 2. Format detection

Workflows in the wild come in three forms:

| Form | Accepts `/prompt`? | Extract with our CLI? |
|---|---|---|
| **API format** `.json` (flat dict keyed by node_id) | YES | N/A — use directly |
| **UI format** `.json` (`{"nodes": [...], "links": [...]}`) | NO — re-export required | Cannot auto-convert in v1 |
| **PNG/WebP with embedded workflow** (standard ComfyUI output) | YES after extraction | `workflow extract IMAGE.png` |

**Detection rule.** A top-level JSON object containing both `"nodes"` (array) and `"links"` (array) is UI format. A top-level JSON object whose values have `"class_type"` and `"inputs"` keys is API format. `workflow validate` applies this rule and surfaces exit 3 with re-export instructions if UI format is detected.

If you land on a UI-format `.json`, the agent's options are:

1. **Ask the user to re-export** via ComfyUI's Dev mode (`Settings → Enable Dev mode Options → Workflow → Export (API Format)`).
2. **Find a PNG output** the workflow produced — drag that image through `workflow extract` instead.
3. **Feed the UI-format JSON back into ComfyUI's web UI** (load it) and let the browser's `graphToPrompt()` conversion happen, then export. This is a human-in-the-loop step; no headless path in v1.

## 3. Extract from a PNG

ComfyUI's default `SaveImage` node embeds TWO chunks in every PNG output:

- `prompt` — the API-format workflow the server executed
- `workflow` — the UI-format graph (so dragging the image back onto the canvas restores the visual editor state)

The skill's `workflow extract` reads both:

```bash
# Default: API format (what you'd submit to /prompt)
comfyui-cli workflow extract output.png > api_workflow.json

# UI format (for loading into the web editor)
comfyui-cli workflow extract output.png --ui > ui_workflow.json

# Both, bundled
comfyui-cli workflow extract output.png --both > bundle.json
```

WebP outputs use EXIF tags instead of PNG chunks — the extractor handles both. APNG (animated PNG) uses private `comf` chunks and IS NOT READABLE via Pillow in v1; if you hit an APNG with no readable workflow, fall back to asking for the source JSON.

**Gotcha:** some third-party save nodes, or ComfyUI launched with `--disable-metadata`, produce images with no embedded workflow. `workflow extract` exits 5 with a clear message in that case.

## 4. Resolve the dependency chain

A freshly downloaded workflow generally fails on the first `queue submit` for one of two reasons:

1. **Missing models** — covered in full in [model-acquisition.md](model-acquisition.md). Run the audit against the workflow JSON, fetch any missing files, place them in the correct folder.
2. **Missing custom nodes** — the workflow references `class_type: "SomeObscureCustomNode"` that ComfyUI doesn't know about. This surfaces as HTTP 400 with `"type": "missing_node_type"` in the `node_errors` body.

### Detecting missing custom nodes

Query `/object_info` for every `class_type` the workflow uses:

```python
import json, httpx

workflow = json.load(open("downloaded.json"))
needed = {node["class_type"] for node in workflow.values() if "class_type" in node}

with httpx.Client(base_url="http://127.0.0.1:8188",
                   headers={"Origin": "http://127.0.0.1:8188"}) as c:
    info = c.get("/object_info").json()

missing = sorted(needed - set(info))
print("Missing node classes:", missing)
```

A class name like `NunchakuFluxDiTLoader` being "missing" means either:
- Its custom node pack isn't installed — install it, OR
- Its custom node pack failed to import at startup — check the startup log for `IMPORT FAILED` entries

### Installing missing custom nodes

The canonical path is **ComfyUI-Manager** (`github.com/ltdrdata/ComfyUI-Manager`), which is already installed on this box. From the web UI: `Manager → Install Custom Nodes → search class name`. For headless installs:

```bash
# Clone the custom node into ComfyUI's custom_nodes/ dir
cd E:/workspaces/tools/comfy/ComfyUI/custom_nodes/
git clone https://github.com/<author>/<node_repo>.git

# Install its Python deps into the ComfyUI venv
cd <node_repo>
# Most nodes ship a requirements.txt
uv pip install --python /e/workspaces/tools/comfy/ComfyUI/.venv/Scripts/python.exe \
  -r requirements.txt

# Restart ComfyUI to load the new node
```

ComfyUI-Manager's catalog (`model-list.json`, `custom-node-list.json`) is the source of truth for "what class maps to what repo". It's published at <https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json> — fetching this JSON and grepping for a class name is the fastest way to resolve `class_type → github repo`.

### Python-package dependency quirks

Some custom nodes require specific Python packages that are:

- **Not on PyPI at all** — e.g. `nunchaku` (the SVDQuant inference library) is distributed only as pre-built wheels from `github.com/nunchaku-tech/nunchaku/releases`. See [model-acquisition.md](model-acquisition.md) for the full gotcha. A `pip install nunchaku` from PyPI installs a *different, unrelated* library.
- **Version-locked to CUDA/torch combos** — `nunchaku-1.2.1+cu13.0torch2.11-cp312-cp312-win_amd64.whl` is a different wheel from `nunchaku-1.2.1+cu12.8torch2.10-cp312-cp312-win_amd64.whl`. Read the custom node's GitHub README; don't guess.
- **Conflicting with existing env** — the ComfyUI venv already has pinned versions of `transformers`, `diffusers`, `torch`. Adding a node that forces a downgrade can break other nodes. Prefer adding in a throwaway env first, verify, then commit the change to the main venv.

## 5. End-to-end: "find me a Flux schnell workflow and run it"

A complete acquisition flow using this skill:

```bash
# 1. Pull a canonical example
curl -L -o /tmp/flux_schnell.png \
  "https://comfyanonymous.github.io/ComfyUI_examples/flux/flux_schnell_example.png"

# 2. Extract the API workflow
comfyui-cli workflow extract /tmp/flux_schnell.png > /tmp/flux.json

# 3. Validate (detects UI format, catches broken links)
comfyui-cli workflow validate /tmp/flux.json

# 4. Audit required models (see model-acquisition.md for the script)
python -c "
import json
needed = []
AUDIT_KEYS = {'CheckpointLoaderSimple': 'ckpt_name', 'UNETLoader': 'unet_name',
              'LoraLoader': 'lora_name', 'VAELoader': 'vae_name'}
wf = json.load(open('/tmp/flux.json'))
for node in wf.values():
    key = AUDIT_KEYS.get(node.get('class_type'))
    if key and node.get('inputs', {}).get(key):
        needed.append((node['class_type'], node['inputs'][key]))
for c, f in needed:
    print(f'  {c}: {f}')"

# 5. Check what's on the server
comfyui-cli model list --json > /tmp/installed.json

# 6. Diff needed vs installed — acquire missing files per model-acquisition.md
# (manual step or scripted — skill doesn't auto-download models in v1)

# 7. Run it
comfyui-cli workflow run /tmp/flux.json --output-dir /tmp/out
```

## Gotchas

### "Example" workflows that reference non-example models

A workflow pulled from civitai or reddit will usually reference the exact model filename that was on the creator's machine (e.g. `juggernautXL_v8Rundiffusion.safetensors`). If you don't have that exact file, either (a) acquire it (Civitai model page) or (b) use `workflow set` to swap to a similar checkpoint you DO have:

```bash
comfyui-cli workflow set /tmp/flux.json \
  --param @Checkpoint.ckpt_name=flux1-schnell-fp8.safetensors \
  -o /tmp/flux_swapped.json
```

Quality will differ — a workflow authored for a specific LoRA stack on top of a specific base model cannot be swapped 1:1 for an arbitrary checkpoint and still produce the reference image.

### Stale workflows referencing removed nodes

Custom node packs get renamed, forked, or abandoned. A two-year-old workflow may reference `ImpactPack.FaceDetailer` while today's install has `ComfyUI-Impact-Pack.FaceDetailer` — same behavior, different class registration. The workflow's JSON is a *snapshot* of the runtime that produced it; when that runtime has drifted, expect `missing_node_type` errors and plan to edit the workflow or install the archived version of the pack.

### Workflows with embedded secrets

Some creators' workflows accidentally include `api_key_comfy_org` or `auth_token_comfy_org` in `extra_data`. The ComfyUI server strips these before storing them (per `SENSITIVE_EXTRA_DATA_KEYS` at `execution.py:151`), but the downloaded JSON file on disk still contains them. Scan workflows from strangers for obvious secret-looking keys before committing them anywhere.

### Workflow JSON that exceeds server defaults

A few community workflows have 1000+ nodes (heavy masking pipelines, batch comparison grids). `aiohttp`'s default `client_max_size` is 100 MB, which is fine for JSON but some workflows embed base64-encoded source images that push past it. If `queue submit` returns a 413-class error, the fix is to host the image separately and use `LoadImage` with a filename instead of embedding.

### Frontend-only node shapes

Reroute and primitive nodes exist in UI format but are "dissolved" during `graphToPrompt()` conversion. If you see a `.json` with `type: "Reroute"` or `type: "PrimitiveNode"`, it's UI format — no API-format workflow carries those. Re-export.

## Source URLs

- ComfyUI example gallery: <https://comfyanonymous.github.io/ComfyUI_examples/>
- Comfy-Org workflow templates: <https://github.com/Comfy-Org/workflow_templates>
- Comfy-Org fp8 checkpoint repos: <https://huggingface.co/Comfy-Org>
- ComfyUI-Manager catalog (for class_type → repo resolution): <https://github.com/ltdrdata/ComfyUI-Manager>
- Custom-node-list JSON: <https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json>
- Civitai workflow browser: <https://civitai.com/models?tag=workflow>
- OpenArt.ai workflow browser: <https://openart.ai/workflows/home>
- `execution.py:1065-1184` — `validate_prompt` and the `missing_node_type` error type
- `execution.py:151` — `SENSITIVE_EXTRA_DATA_KEYS` for secret-stripping
