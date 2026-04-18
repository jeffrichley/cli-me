---
title: ComfyUI Workflow Parameter Substitution
description: Addressing and mutating workflow inputs by node ID or title.
---

# ComfyUI Workflow Parameter Substitution

## Overview

A ComfyUI **API-format** workflow is a JSON object of the shape:

```json
{
  "3": {
    "inputs": {
      "seed": 0,
      "steps": 20,
      "cfg": 8.0,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1.0,
      "model":        ["4", 0],
      "positive":     ["6", 0],
      "negative":     ["7", 0],
      "latent_image": ["5", 0]
    },
    "class_type": "KSampler",
    "_meta": { "title": "KSampler" }
  }
}
```

Every node is keyed by a string `node_id`. Each node has:

- `inputs` — a dict whose keys come from the node class's `INPUT_TYPES["required"]` (and `["optional"]`) keys. Scalar values are set directly (`"seed": 1234`); link values are a `[source_node_id, output_index]` pair.
- `class_type` — the Python class name that implements the node (e.g. `"KSampler"`).
- `_meta.title` — OPTIONAL human label shown in the UI. Workflow authors rename nodes here. Real API exports (see `ComfyUI/script_examples/basic_api_example.py`) frequently omit `_meta` entirely. When `_meta` is absent, `@Title.key` addressing falls back to `class_type` (same semantics as `class:ClassName.key`). For maximum portability, prefer `NODE_ID.key`.

To change a parameter, you find a node and set `inputs["<key>"] = <value>`. All parameter substitution in this skill is **local JSON surgery** — nothing is sent to the server until `comfyui run`.

## Addressing scheme

The CLI accepts `--param KEY=VALUE` where `KEY` is one of three forms:

| Form | Example | Matches |
|---|---|---|
| `NODE_ID.input_key` | `--param 3.seed=1234567` | node whose JSON key equals `"3"` — parser uses `lsplit('.', 1)` (node ids cannot contain `.`) |
| `@Title.input_key` | `--param @KSampler.seed=1234567` | the single node whose `_meta.title` equals `Title` (case-sensitive) — **errors if multiple match** |
| `class:CLASS.input_key` | `--param class:KSampler.seed=42` | the single node whose `class_type` equals `CLASS` — **errors if multiple match** |

**Parser rule for `@Title.key`:** the parser MUST `rsplit('.', 1)` so the rightmost token is always `input_key`. A title containing `.` (e.g. `v1.0 Sampler`) is addressed as `@v1.0 Sampler.seed` and the rightmost `.seed` is unambiguously the input key. This differs from `NODE_ID.key` (lsplit) because node ids can't contain dots.

**Ambiguity is an error, not a silent first-wins.** When `@Title` or `class:Class` matches multiple nodes, the CLI MUST abort and print every matching `node_id` + title and tell the user to switch to explicit `NODE_ID.key` addressing.

### Value parsing

The CLI parses the right-hand side as JSON first, then falls back to a string literal:

- `3.seed=42` → int `42`
- `3.denoise=0.75` → float `0.75`
- `3.cfg=8` → int `8` (valid — ComfyUI coerces INT/FLOAT server-side)
- `6.text="a cyberpunk cat"` → string `"a cyberpunk cat"`
- `5.width=1024` → int `1024`
- `9.add_noise=enable` → string `"enable"` (JSON parse fails, fallback to raw)
- `3.noise_seed=true` → bool `true` (rare; most numeric inputs will reject)
- Arrays: `9.some_list='[1,2,3]'` → list

The `KSampler.seed=random` and `KSampler.seed=random64` special tokens (see [Seed handling](#seed-handling)) are resolved **before** JSON parsing.

**Shell escaping examples:**

- bash: `--param 6.text="a cyberpunk cat"`
- PowerShell: `--param 6.text='a "cyberpunk" cat'` (single quotes preserve inner double quotes)
- cmd.exe: wrap in double quotes and escape inner double quotes as `""`: `--param 6.text="a ""cyberpunk"" cat"`

**Argparse negative-number gotcha:** for negative floats like `--param 3.cfg=-1.0`, always use `=` (not a space). `--param 3.cfg -1.0` may be parsed as a flag by argparse and rejected.

## Common nodes cheatsheet

All input keys below are grounded in `E:/workspaces/tools/comfy/ComfyUI/nodes.py` (and `comfy_extras/`). All nodes except `EmptySD3LatentImage` use the legacy `INPUT_TYPES` classmethod. `EmptySD3LatentImage` uses the new `io.Schema` declaration (`comfy_extras/nodes_sd3.py:~39`). The `/object_info` response shape is identical from the client's perspective — both forms surface min/max/step/default. `class_type` strings in workflows equal the Python class name exactly.

### `CheckpointLoaderSimple` — nodes.py:588

| input_key | type | typical value |
|---|---|---|
| `ckpt_name` | STRING (combo from `folder_paths.get_filename_list("checkpoints")`) | `"sd_xl_base_1.0.safetensors"` |

Source: `nodes.py:593`.

### `CLIPTextEncode` — nodes.py:59

| input_key | type | typical value |
|---|---|---|
| `text` | STRING (multiline, dynamicPrompts) | `"a photo of a cat, cinematic lighting"` |
| `clip` | CLIP link | `["4", 1]` |

Source: `nodes.py:64-65`.

### `KSampler` — nodes.py:1564

| input_key | type | typical value |
|---|---|---|
| `model` | MODEL link | `["4", 0]` |
| `seed` | INT uint64 (min 0, max `0xffffffffffffffff`) | `0` |
| `steps` | INT (default 20, min 1, max 10000) | `20` |
| `cfg` | FLOAT (default 8.0, min 0.0, max 100.0, step 0.1) | `8.0` |
| `sampler_name` | STRING combo (`comfy.samplers.KSampler.SAMPLERS`) | `"euler"` |
| `scheduler` | STRING combo (`comfy.samplers.KSampler.SCHEDULERS`) | `"normal"` |
| `positive` | CONDITIONING link | `["6", 0]` |
| `negative` | CONDITIONING link | `["7", 0]` |
| `latent_image` | LATENT link | `["5", 0]` |
| `denoise` | FLOAT (default 1.0, min 0.0, max 1.0) | `1.0` |

Source: `nodes.py:1569-1578`.

**Note:** `control_after_generate` is a **UI-only widget hint** (`{"control_after_generate": True}` on the `seed` input at `nodes.py:1570`). It does **not** appear in API-format `inputs` — do not `--param` it.

### `KSamplerAdvanced` — nodes.py:1593

| input_key | type | typical value |
|---|---|---|
| `model` | MODEL link | `["4", 0]` |
| `add_noise` | combo `["enable","disable"]` | `"enable"` |
| `noise_seed` | INT uint64 (min 0, max `0xffffffffffffffff`) | `0` |
| `steps` | INT (default 20) | `20` |
| `cfg` | FLOAT (default 8.0) | `8.0` |
| `sampler_name` | STRING combo | `"euler"` |
| `scheduler` | STRING combo | `"normal"` |
| `positive` | CONDITIONING link | `["6", 0]` |
| `negative` | CONDITIONING link | `["7", 0]` |
| `latent_image` | LATENT link | `["5", 0]` |
| `start_at_step` | INT (default 0) | `0` |
| `end_at_step` | INT (default 10000) | `10000` |
| `return_with_leftover_noise` | combo `["disable","enable"]` | `"disable"` |

Source: `nodes.py:1596-1609`.

### `EmptyLatentImage` — nodes.py:1214

| input_key | type | typical value |
|---|---|---|
| `width` | INT (default 512, min 16, max MAX_RESOLUTION=16384, step 8) | `512` |
| `height` | INT (default 512, min 16, max MAX_RESOLUTION=16384, step 8) | `512` |
| `batch_size` | INT (default 1) | `1` |

Source: `nodes.py:1219-1221`.

### `EmptySD3LatentImage` — comfy_extras/nodes_sd3.py:39

| input_key | type | typical value |
|---|---|---|
| `width` | INT (default 1024, min 16, max MAX_RESOLUTION=16384, step 16) | `1024` |
| `height` | INT (default 1024, min 16, max MAX_RESOLUTION=16384, step 16) | `1024` |
| `batch_size` | INT (default 1) | `1` |

Source: `comfy_extras/nodes_sd3.py:46-48`. Uses the new `io.Schema` declaration, not `INPUT_TYPES`. Use for SD3 / Flux workflows — produces a 16-channel latent instead of 4.

### `VAEDecode` — nodes.py:294

| input_key | type | typical value |
|---|---|---|
| `samples` | LATENT link | `["3", 0]` |
| `vae` | VAE link | `["4", 2]` |

Source: `nodes.py:299-300`. All inputs are links — rarely `--param`'d.

### `VAEEncode` — nodes.py:354

| input_key | type | typical value |
|---|---|---|
| `pixels` | IMAGE link | `["10", 0]` |
| `vae` | VAE link | `["4", 2]` |

Source: `nodes.py:357`.

### `SaveImage` — nodes.py:1627

| input_key | type | typical value |
|---|---|---|
| `images` | IMAGE link | `["8", 0]` |
| `filename_prefix` | STRING (default `"ComfyUI"`) | `"my_run"` |

Source: `nodes.py:1638-1639`. Supports `%date:yyyy-MM-dd%` and `%NodeTitle.input%` substitutions server-side.

### `LoadImage` — nodes.py:1700

| input_key | type | typical value |
|---|---|---|
| `image` | STRING (combo from `input/` dir listing) | `"photo.png"` |

Source: `nodes.py:1707`. Path is relative to `folder_paths.get_input_directory()`.

### `LoraLoader` — nodes.py:671

| input_key | type | typical value |
|---|---|---|
| `model` | MODEL link | `["4", 0]` |
| `clip` | CLIP link | `["4", 1]` |
| `lora_name` | STRING combo (`get_filename_list("loras")`) | `"anime_style.safetensors"` |
| `strength_model` | FLOAT (default 1.0, range -100.0..100.0 — negatives valid) | `0.8` |
| `strength_clip` | FLOAT (default 1.0, range -100.0..100.0 — negatives valid) | `1.0` |

Source: `nodes.py:681-685`.

### `LoraLoaderModelOnly` — nodes.py:716

| input_key | type | typical value |
|---|---|---|
| `model` | MODEL link | `["4", 0]` |
| `lora_name` | STRING combo | `"flux_lora.safetensors"` |
| `strength_model` | FLOAT (default 1.0) | `1.0` |

Source: `nodes.py:719-721`.

### `ControlNetLoader` — nodes.py:834

| input_key | type | typical value |
|---|---|---|
| `control_net_name` | STRING combo (`get_filename_list("controlnet")`) | `"control_sd15_canny.pth"` |

Source: `nodes.py:837`.

### `CLIPSetLastLayer` — nodes.py:655

| input_key | type | typical value |
|---|---|---|
| `clip` | CLIP link | `["4", 1]` |
| `stop_at_clip_layer` | INT (default -1, min -24, max -1) | `-2` |

Source: `nodes.py:658-659`.

## Seed handling

Most UI workflows randomize the seed on every run via a `control_after_generate` widget. Because API-format submissions don't carry widget state, **the client is responsible for randomizing the seed** before POSTing.

The skill supports two special tokens (and only these two):

```
--param KSampler.seed=random
--param 3.seed=random
--param @KSampler.noise_seed=random64
```

- `seed=random` — generates a uniform int in `[0, 2**32 - 1]` (32-bit). Matches ComfyUI's web UI "randomize" button.
- `seed=random64` — generates a uniform int in `[0, 2**63 - 1]` (signed int64 range, chosen for downstream JSON safety, see below).

In both cases the CLI:

1. Resolves the token to a concrete integer.
2. Writes the integer into the workflow JSON **before** it is serialized.
3. Prints the chosen seed to stderr so reruns are reproducible.

**Design decision — no other seed tokens.** `seed=now`, `seed=+1`, `seed=increment` are NOT supported in v1. Callers that want monotonic or timestamp-derived seeds should compute the integer themselves and pass it explicitly. This keeps the substitution layer pure and deterministic.

**Why `random` is 32-bit even though KSampler accepts uint64.** KSampler's schema (`nodes.py:1570`) accepts `0 <= seed <= 0xffffffffffffffff` (uint64), but 32 bits matches what the web UI shows users and is enough entropy for image generation. Use `random64` if you explicitly want more.

**Seed JSON precision warning.** KSampler.seed supports values up to `2**64 - 1`, but standard JSON parsers (including JavaScript's `JSON.parse`) downcast integers greater than `2**53` to floats, silently losing precision. Python's `json.loads` preserves full precision. When round-tripping workflows through non-Python tools, keep seeds below `2**53` (`9007199254740992`) — this is why `random64` caps at `2**63 - 1` rather than `2**64 - 1`, and why very large literal seeds should be passed as strings that the skill coerces to int on substitution.

## Validation before submit

The skill can catch most errors locally before calling `POST /prompt`. Do these checks in `comfyui workflow set` and again in `comfyui run`:

**Client-side (fast-fail, no server round trip):**

1. Every link target exists: for every `inputs[k] == [src_id, idx]`, the workflow has a node with key `src_id`.
2. Every `class_type` is a non-empty string.
3. Every node has an `inputs` dict (even if empty).
4. Seeds fit in uint64 (`0 <= seed <= 0xffffffffffffffff`, matching `nodes.py:1570`). Note this is **uint64**, not int64.
5. `--param` key resolves to exactly one node (for `@Title` and `class:`) — ambiguity is an error.
6. Mandatory nodes present: at least one OUTPUT_NODE (e.g. `SaveImage`, `PreviewImage`) — otherwise the server will accept the prompt but produce no output.

**Requires cached `/object_info` (client-side on second run, server round trip on first):**

- `input_key` exists in that node's schema. Without `/object_info` the CLI can only check the key against the current `inputs` dict — which misses optional inputs that aren't wired yet. With a cached `/object_info` response this becomes a true client-side check.

**Server-side only (cannot validate locally without loading Comfy):**

- Whether `ckpt_name` / `lora_name` / `control_net_name` / `vae` actually exists in the user's `models/` folders.
- Whether `sampler_name` is one of `comfy.samplers.KSampler.SAMPLERS` and `scheduler` is one of `SCHEDULERS` (these lists depend on the installed Comfy version).
- Whether link output indices are valid (e.g. `["4", 3]` when `CheckpointLoaderSimple` only has 3 outputs).
- Resolution constraints (`MAX_RESOLUTION`, step alignment).
- Model-specific compatibility (SD3 latent into SD1.5 KSampler, etc.).

Surface server errors clearly: `POST /prompt` returns `{"error": {...}, "node_errors": {...}}` on failure — bubble the `node_errors` dict up to the user keyed by node id.

## CLI Commands

### `comfyui workflow set` — write substitutions to a new file

```bash
comfyui workflow set IN.json \
  --param 3.seed=42 \
  --param 6.text="a cyberpunk cat" \
  --param 5.width=1024 \
  --param 5.height=1024 \
  -o OUT.json
```

### Address by title

```bash
comfyui workflow set IN.json \
  --param @KSampler.seed=random \
  --param @PositivePrompt.text="a serene mountain lake" \
  -o OUT.json
```

### Address by class (single-match only)

```bash
comfyui workflow set IN.json \
  --param class:CheckpointLoaderSimple.ckpt_name=sd_xl_base_1.0.safetensors \
  -o OUT.json
```

Errors with a helpful message if two `CheckpointLoaderSimple` nodes exist — user must use `NODE_ID` or `@Title` to disambiguate.

### In-place edit

```bash
comfyui workflow set --inline IN.json --param 3.seed=random
```

### Chained with run (most common)

```bash
comfyui run IN.json --param 3.seed=random --param 6.text="a dragon"
```

`comfyui run` applies `--param` the same way before POSTing.

## Gotchas

1. **List-typed inputs are rare but exist.** Some custom nodes take an array for a single input. The JSON-first parser handles this (`--param 9.some_list='[1,2,3]'`) but shell quoting matters on Windows PowerShell — use single quotes in bash, double-quoted JSON with escapes in cmd.exe.

2. **`seed=random` must be resolved client-side.** If the CLI forwards the literal string `"random"` into the workflow JSON, ComfyUI's backend will reject the INT input with a type error. The substitution step **must** materialize a concrete integer before `json.dumps`.

3. **`@Title` matching is case-sensitive.** `@KSampler` does not match a node titled `"ksampler"`. Workflows exported by the web UI preserve the UI casing. Print available titles on mismatch.

4. **`@Title` and `class:CLASS` both error on ambiguity.** Two `LoraLoader` nodes for model-and-style stacking is common. Two nodes titled `"KSampler"` is also common (workflow author never renamed them). Both forms must **error, not guess** — print every matching `node_id` + title and tell the user to switch to `NODE_ID.key` addressing.

5. **`control_after_generate` is not an input.** It is a widget-only hint on the `seed` field (`nodes.py:1570`). `--param KSampler.control_after_generate=randomize` will fail validation because no such key exists in `inputs`.

6. **API-format vs UI-format.** This skill only handles **API-format** workflows (flat `{node_id: {...}}`). UI-format exports (with `nodes`, `links`, `groups` arrays) must be converted first — ComfyUI's web UI has "Save (API format)" for this. Error loudly if the top-level JSON has a `nodes` array.

7. **SD3/Flux uses `EmptySD3LatentImage`, not `EmptyLatentImage`.** The two produce incompatible latent shapes (4-channel vs 16-channel). Don't blindly swap `class_type` — rewire the whole latent path.

## Sources

- `E:/workspaces/tools/comfy/ComfyUI/nodes.py` — core node definitions
  - `CLIPTextEncode` — line 59
  - `VAEDecode` — line 294
  - `VAEEncode` — line 354
  - `CheckpointLoaderSimple` — line 588
  - `CLIPSetLastLayer` — line 655
  - `LoraLoader` — line 671
  - `LoraLoaderModelOnly` — line 716
  - `ControlNetLoader` — line 834
  - `EmptyLatentImage` — line 1214
  - `KSampler` — line 1564
  - `KSamplerAdvanced` — line 1593
  - `SaveImage` — line 1627
  - `LoadImage` — line 1700
- `E:/workspaces/tools/comfy/ComfyUI/comfy_extras/nodes_sd3.py`
  - `EmptySD3LatentImage` — line 39
- ComfyUI server API: `POST /prompt` accepts `{"prompt": <workflow>, "client_id": "..."}` — see `ComfyUI/server.py`.
- Upstream reference: <https://github.com/comfyanonymous/ComfyUI/blob/master/nodes.py>
