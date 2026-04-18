---
title: ComfyUI Model Acquisition
description: Identify what models a workflow needs, where to get them, where to put them, and how to refresh ComfyUI's view of the filesystem.
---

# ComfyUI Model Acquisition

When an agent tries to run a workflow it didn't build — pulled from reddit, downloaded off a model page, or generated programmatically — the first thing that often breaks is a missing model file. The `/prompt` server will return HTTP 400 with `node_errors` and a `"value_not_in_list"` error, and the user is stuck. This page documents the end-to-end loop: **audit the workflow → identify the source → download to the right folder → refresh the server.**

All file:line references in this page target the ComfyUI revision recorded in `references/source-analysis/analyzed-version.md`.

## 1. Audit a workflow for required models

Every model a workflow needs is a string-valued input on a loader node. The CLI's wiki already catalogs which node loads which type (see [models-and-assets.md](models-and-assets.md) for the full TYPE → NodeClass table). In practice the five that matter almost every time are:

| Loader node | Input key | Type bucket |
|---|---|---|
| `CheckpointLoaderSimple` | `ckpt_name` | `checkpoints` |
| `UNETLoader` | `unet_name` | `diffusion_models` |
| `LoraLoader` / `LoraLoaderModelOnly` | `lora_name` | `loras` |
| `VAELoader` | `vae_name` | `vae` |
| `CLIPLoader` / `DualCLIPLoader` / `TripleCLIPLoader` | `clip_name` / `clip_name1`..`clip_name3` | `text_encoders` |
| `ControlNetLoader` | `control_net_name` | `controlnet` |
| `CLIPVisionLoader` | `clip_name` | `clip_vision` |
| `StyleModelLoader` | `style_model_name` | `style_models` |
| `UpscaleModelLoader` | `model_name` | `upscale_models` |

### Pseudocode for auditing an API-format workflow

```python
import json

AUDIT_KEYS = {
    "CheckpointLoaderSimple": [("ckpt_name", "checkpoints")],
    "UNETLoader": [("unet_name", "diffusion_models")],
    "LoraLoader": [("lora_name", "loras")],
    "LoraLoaderModelOnly": [("lora_name", "loras")],
    "VAELoader": [("vae_name", "vae")],
    "CLIPLoader": [("clip_name", "text_encoders")],
    "DualCLIPLoader": [("clip_name1", "text_encoders"), ("clip_name2", "text_encoders")],
    "TripleCLIPLoader": [("clip_name1", "text_encoders"), ("clip_name2", "text_encoders"), ("clip_name3", "text_encoders")],
    "ControlNetLoader": [("control_net_name", "controlnet")],
    "CLIPVisionLoader": [("clip_name", "clip_vision")],
    "StyleModelLoader": [("style_model_name", "style_models")],
    "UpscaleModelLoader": [("model_name", "upscale_models")],
}

def audit(workflow: dict) -> list[tuple[str, str]]:
    """Return list of (type_bucket, filename) the workflow requires."""
    needed: list[tuple[str, str]] = []
    for _node_id, node in workflow.items():
        mapping = AUDIT_KEYS.get(node.get("class_type"))
        if not mapping:
            continue
        inputs = node.get("inputs", {})
        for input_key, bucket in mapping:
            value = inputs.get(input_key)
            if isinstance(value, str) and value:
                needed.append((bucket, value))
    return needed
```

Then cross-reference each `(bucket, filename)` pair against `comfyui model list --type <bucket> --json`:

```bash
# For each needed file, check if it's on the server
comfyui-cli model list --type checkpoints --json | jq -r '.checkpoints[]' | grep -Fx "flux1-schnell-fp8.safetensors" || echo "missing"
```

**Before submitting any unfamiliar workflow, run this audit and resolve every "missing" line first.** The alternative is getting back a `node_errors` blob from `/prompt` after you've already burned time on the request — and for a Flux or SD3 workflow with 4+ loaders, the error message can be ambiguous about which one failed to find its file.

## 2. Identify the source

### Primary sources — use in this order

**HuggingFace Hub** covers roughly everything from model labs (Black Forest Labs, Stability AI, Alibaba, Tencent) plus Comfy-Org's curated fp8 repackagings:

- **Comfy-Org/** — repackaged single-file checkpoints that work with `CheckpointLoaderSimple` (recommended for Flux, SD3.5). Ungated, no auth needed.
  - `Comfy-Org/flux1-schnell` → `flux1-schnell-fp8.safetensors` (17.2 GB, all-in-one)
  - `Comfy-Org/flux1-dev` → `flux1-dev-fp8.safetensors` (17.2 GB, all-in-one) + `split_files/diffusion_models/*-canny-dev.safetensors` etc
  - `Comfy-Org/stable-diffusion-3.5-fp8` — SD3.5 Medium/Large in fp8
- **black-forest-labs/FLUX.1-schnell** / **FLUX.1-dev** — raw fp16 transformers (24 GB), **gated** (click-through license). Use only if the Comfy-Org fp8 isn't sufficient.
- **stabilityai/stable-diffusion-xl-base-1.0** — SDXL base checkpoint. Ungated.
- **city96/FLUX.1-schnell-gguf** / **city96/FLUX.1-dev-gguf** — GGUF quantizations (Q4 ≈ 6 GB, Q8 ≈ 12 GB). Smaller than fp8. Requires the `ComfyUI-GGUF` custom node — see [flow-acquisition.md](flow-acquisition.md) for the custom-node chain.

**Civitai** (`https://civitai.com/`) is the home of community-trained SDXL / SD 1.5 / Flux / Pony checkpoints and LoRAs. Each model page has a "Download" button that produces a direct link. Civitai URLs look like:

```
https://civitai.com/api/download/models/<version_id>
```

Civitai downloads sometimes require an API key for gated/mature content; set `CIVITAI_TOKEN` env var or use `Authorization: Bearer <token>` header.

**GitHub releases** — some specialty models (SVDQuant, nunchaku-flavored Flux, custom inference libraries) live here. Example: `github.com/nunchaku-tech/nunchaku/releases` publishes both the inference library (as wheels) AND the quantized model weights (as `.safetensors`).

**The loader's own HF card** — if the workflow references `Jixar_flux_v2.safetensors` and you don't know where it came from, search HF for the exact filename. Often you land directly on the repo that produced it.

### Example filename → source mapping cheat-sheet

From the live install, these are the real-world sources you'd expect:

| Filename on disk | Likely source |
|---|---|
| `flux1-schnell-fp8.safetensors` | `Comfy-Org/flux1-schnell` |
| `flux1-dev-fp8.safetensors` | `Comfy-Org/flux1-dev` |
| `svdq-int4_r32-flux.1-kontext-dev.safetensors` | `nunchaku-tech/nunchaku-flux.1-kontext-dev` on HF |
| `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` |
| `t5xxl_fp8_e4m3fn.safetensors` | `comfyanonymous/flux_text_encoders` |
| `clip_l.safetensors` | `comfyanonymous/flux_text_encoders` |
| `ae.safetensors` | `black-forest-labs/FLUX.1-schnell` (redistributed) or `Comfy-Org/flux1-schnell/split_files/vae/ae.safetensors` |
| `4x-UltraSharp.pth` | `Kim2091/UltraSharp` on HF, or `lokinfey/Upscale-Hub` mirror |
| Any `*.safetensors` tagged "LoRA" | Civitai model page |

## 3. Download

### HuggingFace Hub (via `huggingface-cli` — canonical)

```bash
# Ungated, direct download
huggingface-cli download \
  Comfy-Org/flux1-schnell \
  flux1-schnell-fp8.safetensors \
  --local-dir E:/data/comfy/models/checkpoints

# For multi-file downloads (e.g. pulling all of split_files/diffusion_models/)
huggingface-cli download \
  Comfy-Org/flux1-dev \
  --include "split_files/diffusion_models/*" \
  --local-dir E:/data/comfy/models/diffusion_models
```

For **gated** repos (anything under `black-forest-labs/` or similar), first accept the license on the HF web UI, then either:
- Run `huggingface-cli login` to cache a token, **or**
- Set `HF_TOKEN` env var before the download command.

### Civitai (via `curl`)

```bash
# Unauthenticated (public models)
curl -L "https://civitai.com/api/download/models/<version_id>" \
  -o E:/data/comfy/models/checkpoints/my_model.safetensors

# With API token
curl -L -H "Authorization: Bearer $CIVITAI_TOKEN" \
  "https://civitai.com/api/download/models/<version_id>" \
  -o E:/data/comfy/models/loras/my_lora.safetensors
```

Civitai responds with a `Content-Disposition` header containing the original filename — use `curl -OJ` if you want to keep it:

```bash
curl -LOJ "https://civitai.com/api/download/models/<version_id>"
```

### GitHub releases (wheel + model file)

```bash
curl -L -o path/to/dest.ext \
  "https://github.com/ORG/REPO/releases/download/vX.Y.Z/filename.ext"
```

## 4. Place it in the right folder

This is the step agents get wrong most often. The `checkpoints/` directory is **not** a catch-all — it means specifically "files that load with `CheckpointLoaderSimple` (single-file, bundled unet+clip+vae)". Flux files ship in two flavors:

| Variant | Folder | Loader node |
|---|---|---|
| **All-in-one** (`flux1-schnell-fp8.safetensors` from `Comfy-Org/flux1-schnell` — bundled unet+clip+vae) | `checkpoints/` | `CheckpointLoaderSimple` |
| **Split** (bare transformer, ~12-24 GB; requires separate CLIP-L, T5, and VAE) | `diffusion_models/` | `UNETLoader` |

Same applies to SD3, Flux Kontext variants (SVDQuant), and all WAN / Hunyuan / AllegroDiffusion models — those are UNETs in `diffusion_models/`.

### Full folder map

See [models-and-assets.md](models-and-assets.md) for the authoritative 21-key table. The high-signal subset:

| Target folder | For what files |
|---|---|
| `checkpoints/` | Single-file SDXL / SD1.5 / Flux-all-in-one checkpoints |
| `diffusion_models/` | Standalone UNETs (split Flux/SD3, WAN, HunyuanVideo, Kontext) |
| `unet/` | Legacy alias for `diffusion_models/` — works, but new files should go in `diffusion_models/` |
| `loras/` | All LoRAs regardless of base model |
| `vae/` | Standalone VAEs (`ae.safetensors`, `sdxl_vae.safetensors`) |
| `text_encoders/` | CLIP-L, T5XXL, UMT5, etc. Legacy alias: `clip/` |
| `clip_vision/` | CLIP-Vision encoders (for IP-Adapter, PhotoMaker, etc.) — DISTINCT from `text_encoders/` |
| `controlnet/` | ControlNet adapters |
| `upscale_models/` | ESRGAN/UltraSharp-style upscalers (`.pth`) |
| `style_models/` | Flux Redux, PhotoMaker style models |
| `embeddings/` | Textual inversion embeddings |

The authoritative source for these paths is `folder_paths.py` — if you need to be absolutely sure, `get_folder_paths(key)` returns the resolved absolute paths, and `extra_model_paths.yaml` can redirect individual keys to shared drives (as this install does — everything lives on `E:\data\comfy\models\`, not inside the ComfyUI tree).

## 5. Refresh ComfyUI's view

Once the file is on disk, ComfyUI needs to notice it. Two mechanisms:

**Automatic (preferred).** `folder_paths.cache_helper` is mtime-aware on the *directory*. If the download changes the directory's mtime (which happens whenever a new file is added), the next `/object_info` request re-scans the directory. Verified in this session: Flux schnell appeared under `model list --type checkpoints` immediately after `huggingface-cli` finished, with no restart.

**Manual.** Some operations don't bump the directory mtime — Windows handles this differently from POSIX in certain FS configurations, and network filesystems can lag. If `model list` doesn't show your new file within ~10 seconds of the download finishing:

1. Try hitting `/object_info/<LoaderNode>` directly — e.g. `curl -H "Origin: <url>" <url>/object_info/CheckpointLoaderSimple`. This forces a recheck.
2. If that still doesn't work, restart ComfyUI. The `cache_helper` is a single module-level instance, so restart is the cleanest invalidation.

No in-ComfyUI-core HTTP endpoint explicitly triggers a refresh. `ComfyUI-Manager` custom node adds one (`/customnode/refresh_all`), but that's out of scope.

## 6. Troubleshooting: `node_errors: value_not_in_list`

When `comfyui queue submit` returns exit 3 with an error body like:

```json
{
  "error": {"type": "prompt_outputs_failed_validation", ...},
  "node_errors": {
    "10": {
      "errors": [{
        "type": "value_not_in_list",
        "message": "Value not in list",
        "details": "ckpt_name: 'flux1-dev-fp8.safetensors' not in ['flux1-schnell-fp8.safetensors']",
        "extra_info": {"input_name": "ckpt_name", "received_value": "flux1-dev-fp8.safetensors"}
      }],
      "class_type": "CheckpointLoaderSimple"
    }
  }
}
```

Read the `class_type` to find the loader, map it back to its folder via the audit table above, and either:

1. **Download the missing file** to the correct folder (section 4), OR
2. **Substitute a similar model** — if the workflow asks for `flux1-dev-fp8.safetensors` and you have `flux1-schnell-fp8.safetensors`, use `comfyui workflow set <file> --param <node_id>.ckpt_name=flux1-schnell-fp8.safetensors` and re-submit. Quality differs (dev does better at multi-step CFG, schnell is 4-step distilled), but for many use cases the substitute is fine.

## Gotchas

### PyPI package name collisions

**The PyPI `nunchaku` package is NOT the ComfyUI-nunchaku SVDQuant library.** It's a completely unrelated Gibbs sampler for Bayesian models. The real inference library is distributed *only* as pre-built wheels from `github.com/nunchaku-tech/nunchaku/releases`, keyed to specific CUDA + torch + Python + OS combinations. Installing the PyPI package masks the real one and still produces `ImportError: cannot import name 'NunchakuFluxTransformer2dModel'` on custom-node load.

General rule: if a custom node fails to import with a specific `ImportError: cannot import name 'X' from 'Y'` message, check whether `Y` on PyPI is actually the project the node expects. The node's GitHub README is the authoritative source for install instructions; `pip install <name>` from PyPI is *often* correct but not always.

### Single-file vs split checkpoints

If a workflow uses `CheckpointLoaderSimple` and you put the file in `diffusion_models/`, it won't find it. Conversely if the workflow uses `UNETLoader` + `DualCLIPLoader` + `VAELoader` separately (the split path) and you put a single-file checkpoint in `diffusion_models/`, the `UNETLoader` will load the transformer weights but the CLIP/VAE components will be silently ignored or error at a later stage.

Read the workflow's loader node's `class_type` before choosing where the file goes.

### Downloads that return HTML pages

Both HF and Civitai occasionally return a login/terms page instead of the actual file when credentials are missing or a rate limit triggers. The download will "succeed" (200 OK) but the resulting `.safetensors` will be 1-5 KB of HTML. Verify with:

```bash
file /path/to/downloaded.safetensors  # should say "data" not "HTML document"
du -h /path/to/downloaded.safetensors  # should match expected GB, not KB
```

### Civitai authentication

Civitai's API requires a token for mature/gated content. Attempting to download without one produces a 401 or a 302 redirect to a login page. Store your token as an env var (`CIVITAI_TOKEN`) rather than embedding it in commands — URLs are logged by proxies and shell history.

### `diffusers` directory vs `diffusion_models/`

The `diffusers/` folder key (in `folder_paths.py`) is for **Hugging Face `diffusers` library** snapshots — each entry is a *directory*, not a file, containing `model_index.json` and sharded weights. This is completely separate from `diffusion_models/` (which is for standalone `.safetensors` UNETs). Don't conflate them.

## CLI commands that help

```bash
# List what's installed per type
comfyui-cli model list --type checkpoints
comfyui-cli model list --type diffusion_models
comfyui-cli model list --type loras
comfyui-cli model list --json                     # summary counts across all 13 types

# Find a specific file across all types
comfyui-cli model find "flux1-schnell"

# Before submitting an unknown workflow, extract and inspect it
comfyui-cli workflow extract someone_elses_cool_image.png > extracted.json
comfyui-cli workflow validate extracted.json      # structural check
# (then audit extracted.json yourself using section 1's script)
```

A dedicated `comfyui workflow audit` command that does the audit automatically would be a natural v2 addition; not in v1.

## Sources

- `folder_paths.py` — 21 folder key registrations (see [models-and-assets.md](models-and-assets.md))
- `execution.py:1065-1184` — `validate_prompt` and the `value_not_in_list` error type
- ComfyUI examples and fp8 repackagings: <https://huggingface.co/Comfy-Org>
- Flux text encoders: <https://huggingface.co/comfyanonymous/flux_text_encoders>
- Civitai API: <https://github.com/civitai/civitai/wiki/REST-API-Reference>
- HuggingFace CLI docs: <https://huggingface.co/docs/huggingface_hub/guides/cli>
- ComfyUI extra model paths example: <https://github.com/comfyanonymous/ComfyUI/blob/master/extra_model_paths.yaml.example>
