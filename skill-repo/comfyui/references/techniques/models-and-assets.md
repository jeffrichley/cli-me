---
title: ComfyUI Model & Asset Discovery
description: Enumerate checkpoints, loras, VAEs, text encoders, etc. via /object_info.
---

# ComfyUI Model & Asset Discovery

ComfyUI exposes a single authoritative source for "what models are installed": the `/object_info` HTTP endpoint. Any model-loader node (e.g. `CheckpointLoaderSimple`, `LoraLoader`, `VAELoader`) declares its available files in the node's `INPUT_TYPES()` schema, populated at import time from `folder_paths.get_filename_list(...)`. The CLI should always prefer `/object_info` over filesystem scanning — it's the same source the ComfyUI web client uses, it transparently honors `extra_model_paths.yaml`, and it works when the server is on a remote host.

## Model folder keys

These are every folder key registered in the stock ComfyUI install. Each key maps to one or more directories (first path wins as the "default" for saves) and an allowed extension set. The global `supported_pt_extensions = {'.ckpt', '.pt', '.pt2', '.bin', '.pth', '.safetensors', '.pkl', '.sft'}` is defined at `folder_paths.py:12`.

| Folder key | Default directory (under `models/`) | Extensions | Source |
|------------|--------------------------------------|------------|--------|
| `checkpoints` | `models/checkpoints` | `supported_pt_extensions` | `folder_paths.py:23` |
| `configs` | `models/configs` | `.yaml` | `folder_paths.py:24` |
| `loras` | `models/loras` | `supported_pt_extensions` | `folder_paths.py:26` |
| `vae` | `models/vae` | `supported_pt_extensions` | `folder_paths.py:27` |
| `text_encoders` | `models/text_encoders`, `models/clip` (legacy) | `supported_pt_extensions` | `folder_paths.py:28` |
| `diffusion_models` | `models/unet`, `models/diffusion_models` | `supported_pt_extensions` | `folder_paths.py:29` |
| `clip_vision` | `models/clip_vision` | `supported_pt_extensions` | `folder_paths.py:30` |
| `style_models` | `models/style_models` | `supported_pt_extensions` | `folder_paths.py:31` |
| `embeddings` | `models/embeddings` | `supported_pt_extensions` | `folder_paths.py:32` |
| `diffusers` | `models/diffusers` | `["folder"]` (directories, not files) | `folder_paths.py:33` |
| `vae_approx` | `models/vae_approx` | `supported_pt_extensions` | `folder_paths.py:34` |
| `controlnet` | `models/controlnet`, `models/t2i_adapter` | `supported_pt_extensions` | `folder_paths.py:36` |
| `gligen` | `models/gligen` | `supported_pt_extensions` | `folder_paths.py:37` |
| `upscale_models` | `models/upscale_models` | `supported_pt_extensions` | `folder_paths.py:39` |
| `latent_upscale_models` | `models/latent_upscale_models` | `supported_pt_extensions` | `folder_paths.py:41` |
| `custom_nodes` | `custom_nodes/` (under base, not `models/`) | `set()` (any) | `folder_paths.py:43` |
| `hypernetworks` | `models/hypernetworks` | `supported_pt_extensions` | `folder_paths.py:45` |
| `photomaker` | `models/photomaker` | `supported_pt_extensions` | `folder_paths.py:47` |
| `classifiers` | `models/classifiers` | `{""}` (extensionless files) | `folder_paths.py:49` |
| `model_patches` | `models/model_patches` | `supported_pt_extensions` | `folder_paths.py:51` |
| `audio_encoders` | `models/audio_encoders` | `supported_pt_extensions` | `folder_paths.py:53` |

Legacy aliases: `unet` → `diffusion_models`, `clip` → `text_encoders` (`folder_paths.py:97-100`, handled by `map_legacy()`).

Custom node packs register additional keys at import time via `folder_paths.add_model_folder_path(folder_name, full_folder_path, is_default)` (`folder_paths.py:281`). The CLI must not hardcode the list — always enumerate `folder_names_and_paths.keys()` or drive off `/object_info`.

## `/object_info` anatomy

```
GET /object_info                  → dict keyed by node class name, all nodes
GET /object_info/{node_class}     → single-entry dict for one node
```

Source: `server.py:744-763`. The per-node payload is assembled by `node_info()` (`server.py:695-742`). For a model-loader node, a typical response looks like this:

> **V3 `_ComfyNodeInternal` divergence:** nodes whose class subclasses `_ComfyNodeInternal` (V3-style, new `io.Schema` API — e.g. `TripleCLIPLoader`, `QuadrupleCLIPLoader`) are serialized via `obj_class.GET_NODE_INFO_V1()` at `server.py:697-698` instead of the legacy `INPUT_TYPES()`-based assembler. V3 nodes may emit either the legacy shape `[[values], {options}]` OR the COMBO shape `["COMBO", {"options": [values], "multiselect": false, ...}]`. The extractor MUST handle both: check `isinstance(spec[0], str)` — if it's a string, it's the V3 type tag and the values live at `spec[1]["options"]`; otherwise fall back to the legacy path (`spec[0]` is the value list). Verified on a stock ComfyUI 0.19.x install: `TripleCLIPLoader` returns the COMBO shape while `CLIPLoader` / `DualCLIPLoader` still return legacy. Reading `spec[0]` and treating it as a list without the string check silently loses every V3 loader's filenames.

```json
{
  "CheckpointLoaderSimple": {
    "input": {
      "required": {
        "ckpt_name": [
          ["sdxl_base_1.0.safetensors", "flux1-dev.safetensors", "sd15.ckpt"],
          {"tooltip": "The name of the checkpoint (model) to load."}
        ]
      }
    },
    "input_order": {"required": ["ckpt_name"]},
    "output": ["MODEL", "CLIP", "VAE"],
    "output_is_list": [false, false, false],
    "output_name": ["MODEL", "CLIP", "VAE"],
    "name": "CheckpointLoaderSimple",
    "display_name": "Load Checkpoint",
    "description": "Loads a diffusion model checkpoint, diffusion models are used to denoise latents.",
    "python_module": "nodes",
    "category": "loaders",
    "output_node": false
  }
}
```

Key shape detail: `input.required.<param>` is a **two-element list** (from a Python tuple). The first element is either:

- a **list of strings** — the dropdown values (filenames, for loader nodes), or
- a **type name string** like `"INT"`, `"FLOAT"`, `"STRING"`, `"MODEL"`, `"CLIP"` — a typed socket.

The second element is an options dict (`tooltip`, `default`, `min`, `max`, `multiline`, etc.).

**Canonical extraction rule.** A naive `isinstance(values, list)` check is wrong: a typed socket like `("LATENT",)` serializes to JSON as `["LATENT"]` — a 1-element list of strings — and would be mistaken for a single-entry enum/dropdown. Extraction must also handle the V3 COMBO shape where `spec[0]` is the string `"COMBO"` and values live under `spec[1]["options"]`. Use this instead:

```python
def is_enum(values) -> bool:
    if not isinstance(values, list) or not values:
        return False
    first = values[0]
    # Typed sockets are always list-of-uppercase-strings like ["LATENT"], ["MODEL"], ["CLIP"].
    if (
        len(values) == 1
        and isinstance(first, str)
        and first.isupper()
        and first.replace("_", "").isalnum()
    ):
        return False
    return True

def model_list_from_object_info(node_info: dict, param: str) -> list[str]:
    spec = node_info["input"]["required"][param]
    if not isinstance(spec, list) or not spec:
        return []
    first = spec[0]
    # V3 COMBO shape: ["COMBO", {"options": [...], "multiselect": false, ...}]
    if isinstance(first, str):
        if len(spec) >= 2 and isinstance(spec[1], dict):
            options = spec[1].get("options")
            if isinstance(options, list):
                return [x for x in options if isinstance(x, str)]
        return []
    # Legacy shape: [[values], {options}]
    return list(first) if is_enum(first) else []
```

Source: `CheckpointLoaderSimple.INPUT_TYPES` at `nodes.py:588-595` shows how the filename list is embedded:
```python
"ckpt_name": (folder_paths.get_filename_list("checkpoints"), {"tooltip": "..."})
```

## How to answer "what checkpoints are available?"

**Preferred — HTTP, works locally or remote:**

```
GET http://<host>:8188/object_info/CheckpointLoaderSimple
→ resp["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
```

Per-model-type node mapping the CLI uses:

| `--type` | Node class | Input param |
|----------|-----------|-------------|
| `checkpoints` | `CheckpointLoaderSimple` | `ckpt_name` |
| `loras` | `LoraLoader` | `lora_name` |
| `vae` | `VAELoader` | `vae_name` |
| `text_encoders` | `CLIPLoader` + `DualCLIPLoader` + `TripleCLIPLoader` (union) | `clip_name`, `clip_name1..3` |
| `clip_vision` | `CLIPVisionLoader` | `clip_name` |
| `controlnet` | `ControlNetLoader` | `control_net_name` |
| `upscale_models` | `UpscaleModelLoader` | `model_name` |
| `diffusion_models` | `UNETLoader` | `unet_name` |
| `style_models` | `StyleModelLoader` | `style_model_name` |
| `gligen` | `GLIGENLoader` | `gligen_name` |
| `hypernetworks` | `HypernetworkLoader` | `hypernetwork_name` |
| `photomaker` | `PhotoMakerLoader` | `photomaker_model_name` |

For keys without a stock loader (e.g. `embeddings`, `configs`, `model_patches`, `audio_encoders`, `vae_approx`, `classifiers`, `latent_upscale_models`), fall back to the alternate path below.

**`text_encoders` requires unioning three loaders.** There is no single `CLIPLoader` that exposes every text-encoder file in one call — the three stock loaders differ in arity, not in scope, and each independently calls `folder_paths.get_filename_list("text_encoders")`:

- `CLIPLoader` (`nodes.py:976-1001`) — single-encoder pipelines (SD1, SD2, and any single-encoder `type` like `wan`, `lumina2`, `pixart`, etc.). One param: `clip_name`.
- `DualCLIPLoader` (`nodes.py:1003-1031`) — two-encoder pipelines (SDXL, Flux, HiDream, Hunyuan Video, etc.). Params: `clip_name1`, `clip_name2`.
- `TripleCLIPLoader` (`comfy_extras/nodes_sd3.py:11-36`, V3 `io.ComfyNode`) — three-encoder SD3 (clip-l + clip-g + t5). Params: `clip_name1`, `clip_name2`, `clip_name3`.

For `--type text_encoders` the skill fetches `/object_info/CLIPLoader`, `/object_info/DualCLIPLoader`, `/object_info/TripleCLIPLoader`, extracts the dropdown from each (any one of the `clip_name*` params — all three share the same `text_encoders` filename list within a single loader), and returns the `set()`-union. A stock `QuadrupleCLIPLoader` also exists in `comfy_extras/nodes_hidream.py:9-68` (V3) if four-encoder HiDream needs enumerating.

**Alternate — in-process, same host only:**

```python
import folder_paths
folder_paths.get_filename_list("checkpoints")   # list[str], recursive, deduped
folder_paths.get_folder_paths("checkpoints")    # list[str], search dirs
folder_paths.get_full_path("checkpoints", "sdxl_base_1.0.safetensors")
```

Source: `folder_paths.py:299-301` (`get_folder_paths`), `349-366` (`get_full_path`), `418-426` (`get_filename_list`). This path **only works when the CLI runs inside the ComfyUI Python process or on the same host with `folder_paths` importable**. For any remote ComfyUI, use HTTP.

## `extra_model_paths.yaml`

ComfyUI loads `extra_model_paths.yaml` from its install root at startup (`main.py:97-99`), plus any paths passed via `--extra-model-paths-config` (`main.py:101-103`). Parsing logic lives in `utils/extra_config.py:6-34`.

Format (keys come straight from `folder_paths.py`):

```yaml
my_models:
  base_path: D:/shared/models/         # absolute; ~/ and ${VARS} expanded
  is_default: true                     # these dirs jump to the front of the search list
  checkpoints: models/checkpoints/
  loras: |
    models/loras/
    models/loras_extra/
  text_encoders: |
    models/text_encoders/
    models/clip/
  vae: models/vae/
  controlnet: models/controlnet/
  diffusion_models: |
    models/diffusion_models
    models/unet
  embeddings: models/embeddings/
  upscale_models: models/upscale_models/
  audio_encoders: models/audio_encoders/
  model_patches: models/model_patches/
```

Semantics (`utils/extra_config.py`):

- Top-level keys (`my_models`, `a111`, etc.) are labels only — not used for lookup.
- `base_path` is resolved with `expanduser` + `expandvars`; if relative, resolved against the YAML file's directory.
- Each model-key value is split on newlines; each non-empty line is appended under `base_path` (or taken as-is if absolute) and registered via `add_model_folder_path(key, path, is_default)`.
- `is_default: true` makes these paths take precedence — they're inserted at index `0` of the folder list, and saves/downloads land there (`folder_paths.py:281-297`).
- Existing default directories (e.g. `<comfy>/models/checkpoints`) remain in the search list; `extra_model_paths.yaml` **adds**, it does not replace.

The install the CLI talks to uses this mechanism to redirect `base_path` to a centralized external model store — the CLI only needs to care that `/object_info` already reflects every path the server knows about.

## CLI Commands

```
comfyui model list                       # all folder keys + file counts
comfyui model list --type checkpoints    # filenames for a given model type
comfyui model list --type loras
comfyui model list --type vae
comfyui model find NAME                  # case-insensitive search across all types
```

Implementation notes:

- `model list` (no `--type`): iterate the per-type loader node mapping table above; for each, `GET /object_info/<NodeClass>`, extract `input.required[<param>][0]`, report `key: len(list)`. For keys without a loader, note them as "not enumerable via /object_info" and skip (or use `folder_paths.get_filename_list` if local).
- `model list --type <key>`: single `GET /object_info/<NodeClass>` — do not fetch the full `/object_info` (it builds every node in the registry and is expensive on first call).
- `model find NAME`: fetch all loader node infos once, substring match (case-insensitive) against each list, print `type: filename` rows sorted by type.
- Always treat filenames as opaque relative paths — they may contain forward slashes indicating subdirectories (e.g. `sdxl/base_1.0.safetensors`) because `get_filename_list` is recursive (`folder_paths.py:379-390`).

## Gotchas

1. **Per-folder file-list cache** — `folder_paths.get_filename_list` caches results in the module-level `filename_list_cache` dict (`folder_paths.py:60, 392-426`). The cache is invalidated by checking `os.path.getmtime` on each tracked directory. Adding a file on Linux typically bumps the parent directory's mtime so the cache self-invalidates on the next call, **but on Windows and some network filesystems directory mtimes are not always updated** when a file is dropped in. In that case `/object_info` will keep returning the stale list until ComfyUI restarts. There is **no public HTTP refresh endpoint** (grepped `server.py` — only the request-scoped `cache_helper` context at `server.py:747` exists, which merely dedupes lookups within one response build). Workaround for the CLI: if a `model find` miss looks suspicious, prompt the user to restart ComfyUI or touch the model directory.

2. **Multiple node packs register the same `class_type`** — `NODE_CLASS_MAPPINGS` is a flat dict keyed by string; when two custom node packs both register `CheckpointLoaderSimple` (or another shared name), the last one imported wins silently. The `python_module` field in `/object_info` tells you which module actually owns the node — always log it when the CLI hits a loader so users can diagnose "why are my files different from what the web UI shows".

3. **Remote ComfyUI breaks the `folder_paths` shortcut** — any code path that imports `folder_paths` or touches the filesystem only works when the CLI and server share a host. The CLI must never fall back to local scanning when the configured server is remote; always go through `/object_info`. The `diffusers` key is also special: its "extension" is the literal string `"folder"` (`folder_paths.py:33`) and entries are directories, not files — consumers that blindly filter on file extensions will produce empty lists for it.

4. **`recursive_search` follows symlinks without cycle detection** — the scan that feeds `get_filename_list` uses `os.walk(directory, followlinks=True, topdown=True)` at `folder_paths.py:324`. There is no explicit symlink-cycle guard (only a dup-check on `dirs`-dict mtimes, not a visited-set on the walk). A symlink loop under a tracked models directory will cause infinite recursion / exploding file lists at scan time and freeze the first `/object_info` call. Avoid symlink loops under `E:/data/comfy/models/` (and any `base_path` registered via `extra_model_paths.yaml`).

5. **Windows backslash paths in `extra_model_paths.yaml`** — YAML treats `\` as an escape character inside **double-quoted** strings, so `base_path: "C:\data\comfy\models\"` will silently mangle. Use one of: unquoted `base_path: C:/data/comfy/models/`, forward-slash quoted `base_path: "C:/data/comfy/models/"`, single-quoted `base_path: 'C:\data\comfy\models\'` (single quotes don't process escapes), or doubled backslashes `"C:\\data\\comfy\\models\\"`. Forward slashes are the least error-prone on Windows since Python's path APIs accept them transparently.

6. **Concurrent `/object_info` requests can race the cold-start cache** — `folder_paths.cache_helper` is used as a context manager inside `get_object_info` (`server.py:747-755`) to dedupe filesystem scans within one response, but it is a single module-level instance with no lock. Two concurrent `/object_info` requests during cold start can both enter the context, both trigger disk walks, and in principle interleave writes to the shared dict. In practice `/object_info` is hit once by the web client on connect, so the race is rare — but the CLI should not hammer `/object_info` in parallel on a cold server. Prefer one warm-up call, then per-node `/object_info/{node_class}` queries.

## Sources

- `E:\workspaces\tools\comfy\ComfyUI\folder_paths.py` — all folder key registrations (lines 12-53), `add_model_folder_path` (281), `get_folder_paths` (299), `get_full_path` (349), `get_filename_list` (418), cache (60, 392)
- `E:\workspaces\tools\comfy\ComfyUI\server.py` — `/object_info` routes (744-763), `node_info()` builder (695-742)
- `E:\workspaces\tools\comfy\ComfyUI\nodes.py` — `CheckpointLoaderSimple.INPUT_TYPES` (588-595) as the canonical model-list shape
- `E:\workspaces\tools\comfy\ComfyUI\utils\extra_config.py` — `load_extra_path_config` (6-34)
- `E:\workspaces\tools\comfy\ComfyUI\main.py` — startup hook for `extra_model_paths.yaml` (97-103)
- `E:\workspaces\tools\comfy\ComfyUI\extra_model_paths.yaml.example` — config format reference
- ComfyUI docs — node schema: https://docs.comfy.org/custom-nodes/backend/server_overview#object-info
- GitHub source — https://github.com/comfyanonymous/ComfyUI/blob/master/folder_paths.py and https://github.com/comfyanonymous/ComfyUI/blob/master/server.py
