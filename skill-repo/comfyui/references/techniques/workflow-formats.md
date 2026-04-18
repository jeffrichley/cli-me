---
title: ComfyUI Workflow Formats
description: UI vs API format, PNG metadata extraction, and which the /prompt endpoint accepts.
---

# ComfyUI Workflow Formats

ComfyUI has two JSON representations of a workflow that are NOT interchangeable, and every generated image has both of them embedded inside it. This page pins down the distinction, shows how to pull either one out of an output file, and explains why v1 of this skill refuses to "convert" between them.

All file:line references point into the revision recorded in `references/source-analysis/analyzed-version.md` (ComfyUI `v0.19.0`, commit `acd7185`).

## The two JSON formats

ComfyUI ships two completely different workflow serializations. The web UI uses one; the `/prompt` HTTP endpoint uses the other.

| Aspect | UI format ("workflow") | API format ("prompt") |
|---|---|---|
| Top-level shape | Object with fixed keys | Object keyed by node id (strings) |
| Required top-level keys | `last_node_id`, `last_link_id`, `nodes`, `links`, `groups`, `config`, `extra`, `version` | (none — every key IS a node id) |
| Node representation | Array entry `{id, type, pos, size, flags, order, mode, inputs, outputs, properties, widgets_values}` under `nodes` | `{"inputs": {...}, "class_type": "...", "_meta": {"title": "..."}}` under the node id |
| Connections | Explicit array `links`: `[link_id, from_node, from_slot, to_node, to_slot, type]` | Implicit: an input value `[source_node_id, source_slot_index]` is a connection; any other value is a widget value |
| Widget values | Positional list `widgets_values` ordered by the node's widget definition | Named keys inside `inputs` (e.g. `"seed": 1234`) |
| Reroute/primitive nodes | Present as regular graph nodes | Already collapsed away during export |
| Bypassed / muted nodes | Present with `mode` flag | Already removed during export |
| Produced by | "Save" button in the web UI | "Export (API Format)" (Dev mode) OR `graphToPrompt()` client-side |
| Accepted by `POST /prompt` | NO (server rejects — no `class_type`) | YES — this is the canonical payload |

**Rule of thumb.** If the JSON has `"nodes": [...]` and `"links": [...]` at the top level, it's UI format. If it's a flat dict whose values have `"class_type"`, it's API format.

## How to get API format from the UI

The web UI hides the API-format export behind a settings toggle. In `v0.19.0`:

1. Start ComfyUI and open the web UI (default `http://127.0.0.1:8188`).
2. Click the settings cog. Under the **Comfy** category, enable **"Enable Dev mode Options"** (the toggle that exposes experimental workflow actions).
3. A new menu entry appears in the Workflow menu (top of the canvas): **"Export (API Format)"**. Depending on the installed frontend version this may also appear under File → **Save (API Format)**.
4. Save the resulting `.json` somewhere. That file is what `POST /prompt` wants (wrapped as `{"prompt": <json>}` — see `script_examples/basic_api_example.py`).

If Dev mode is not available in your UI, skip the whole export dance and pull the API format straight out of an existing generated image — see the next section.

## PNG / WebP embedded metadata — the v1 superpower

Every image ComfyUI generates with the default `SaveImage` node carries both workflow formats inside it as side-channel metadata. This is the single most important fact for this skill: **you almost never need to ask the user for a workflow file — you can just read one out of any output image they already have.**

### PNG: text chunks named `prompt` and `workflow`

`SaveImage.save_images` builds a `PngInfo` and calls `add_text("prompt", ...)` for the API-format workflow, then iterates `extra_pnginfo` and adds each key as its own text chunk — and the UI always passes the UI-format workflow under the key `workflow` (`nodes.py:1665-1674`):

```python
# nodes.py:1665-1670 (paraphrased with real identifiers)
metadata = PngInfo()
if prompt is not None:
    metadata.add_text("prompt", json.dumps(prompt))       # API format
if extra_pnginfo is not None:
    for x in extra_pnginfo:
        metadata.add_text(x, json.dumps(extra_pnginfo[x]))  # "workflow" key -> UI format
img.save(path, pnginfo=metadata, compress_level=self.compress_level)
```

The newer helper in `comfy_api/latest/_ui.py:85-95` (`ImageSaveHelper._create_png_metadata`) does the same thing for v3 nodes. The chunk name `prompt` is hardcoded; the key `workflow` is set by the server when it populates `extra_pnginfo` for each job.

Extracting either format with Pillow is a two-liner:

```python
from PIL import Image
import json

def _load_chunk(v):
    # Pillow >= 9 normally returns str for tEXt, but some chunk types / versions yield bytes.
    if isinstance(v, bytes):
        v = v.decode("utf-8")
    return json.loads(v) if v else None

img = Image.open("cool_output.png")
api_workflow = _load_chunk(img.info.get("prompt"))       # API format — submit this
ui_workflow  = _load_chunk(img.info.get("workflow"))     # UI format — open in web UI
```

`Image.info` on a PNG exposes every `tEXt`/`zTXt`/`iTXt` chunk by name. No third-party deps required.

**Repeated-key chunks.** If multiple `tEXt` chunks share a keyword, Pillow's `Image.info` keeps only the last value. ComfyUI writes each key once (see `_ui.py:85-95`), so this isn't a current issue — but third-party post-processors may insert duplicates.

**`iTXt` with language/translation-key fields.** ComfyUI writes plain `tEXt`. If a third party rewrites to `iTXt` with non-empty language/translation-key, Pillow still keys by keyword in `Image.info`, so extraction still works — but the original format will no longer round-trip.

**Animated PNGs (APNG).** `ImageSaveHelper._create_animated_png_metadata` (`comfy_api/latest/_ui.py:98-120`) uses private `comf` chunks instead of standard `tEXt` (so the metadata survives `after_idat=True`). Pillow does not expose these via `img.info`; you'd have to parse chunks manually. In practice this only affects animated outputs — static PNGs use the simple path.

### WebP: metadata via EXIF (Model / Make tags)

WebP doesn't have PNG text chunks, so ComfyUI stashes the JSON inside EXIF. `ImageSaveHelper._create_webp_metadata` (`comfy_api/latest/_ui.py:122-135`):

- The API-format prompt goes into EXIF tag **`0x0110`** (`Model`) as the string `"prompt:" + json.dumps(prompt)`.
- Each `extra_pnginfo` entry (including the UI-format `workflow`) goes into a descending-tag range starting at **`0x010F`** (`Make`), then `0x010E`, etc., as `"<key>:" + json.dumps(value)`.

So to extract. The `prompt:` string is reliably at `0x0110`, but the `workflow:` slot is NOT guaranteed to be at `0x010F` — `_ui.py:130-134` assigns descending tags in `extra_pnginfo.items()` iteration order, so `workflow` is typically first but only by convention. Scan the descending range and match by prefix:

```python
from PIL import Image
import json

def _parse_prefixed(value, prefix):
    # EXIF values may be str or bytes depending on Pillow version / chunk source.
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if not isinstance(value, str) or not value.startswith(prefix + ":"):
        return None
    _, _, payload = value.partition(":")  # safe even if payload contains colons
    return json.loads(payload)

img = Image.open("cool_output.webp")
exif = img.getexif()

# prompt: fixed at 0x0110 (EXIF Model) per _ui.py:129
api_workflow = _parse_prefixed(exif.get(0x0110), "prompt")

# workflow: search descending from 0x010F (EXIF Make) per _ui.py:131-134 —
# tag order depends on extra_pnginfo dict iteration, so don't hardcode 0x010F.
ui_workflow = None
for tag in range(0x010F, 0x010F - 16, -1):
    ui_workflow = _parse_prefixed(exif.get(tag), "workflow")
    if ui_workflow is not None:
        break

if api_workflow is None and ui_workflow is None:
    raise WorkflowExtractError(
        "No 'prompt:' or 'workflow:' EXIF tag found. "
        "Was the image saved by ComfyUI with metadata enabled?"
    )
```

The `"<key>:" + json` shape is unusual — don't `json.loads()` the raw EXIF value; split on the first colon. If neither `prompt:` nor `workflow:` is present, raise `WorkflowExtractError` — don't silently return `None`. The skill's `workflow extract` CLI must surface this as **exit code 5** (resource not found), distinct from "no workflow requested."

## Why the skill doesn't auto-convert UI → API in v1

"Just convert it" is a trap. The UI → API transformation is done client-side by the frontend function **`graphToPrompt()`** (in the ComfyUI_frontend TypeScript repo, not in this Python tree — this ComfyUI install uses the separate frontend package, so there is no `web/` directory here). `graphToPrompt` does a non-trivial amount of work:

- Walks `links` and rewrites each connected input into the `[source_node_id, source_slot_index]` tuple form.
- Collapses reroute, primitive, and group nodes — they exist in the UI graph but not in the execution graph.
- Removes bypassed/muted nodes and rewires around them.
- For each node, looks up its `class_type` in `/object_info` (a live server endpoint) to learn the ordered list of widget names, then zips those names against the positional `widgets_values` array to produce the named `inputs` dict.
- Substitutes default values for widgets whose value is `undefined`.
- Validates input types against the slot types advertised by `/object_info`.

Reimplementing this in Python would be maybe 400-600 lines, would need a live ComfyUI server for `/object_info`, would drift every time the frontend changes, and would still get edge cases wrong for custom nodes. The right upstream is `graphToPrompt` itself — anyone serious about offline conversion should use it via Node or a headless browser.

**v1 decision.** Detect UI format (top-level keys include both `"nodes"` AND `"links"`, and `"nodes"` is a list) and fail loudly with a message that tells the user to re-export. Example:

```
Error: this looks like a UI-format workflow, which the /prompt endpoint does not accept.

To get an API-format workflow:
  1. Open ComfyUI web UI
  2. Settings -> enable "Enable Dev mode Options"
  3. Workflow menu -> "Export (API Format)"

Or, if you have a generated image lying around, extract the API workflow directly:
  comfyui workflow extract path/to/image.png
```

## Canonical minimal API workflow

The smallest workflow `/prompt` will accept for text-to-image SD 1.5 is the 7-node graph shipped in `script_examples/basic_api_example.py`: `CheckpointLoaderSimple` → `CLIPTextEncode` × 2 → `EmptyLatentImage` → `KSampler` → `VAEDecode` → `SaveImage`. Pretty-printed:

```json
{
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "cfg": 8,
      "denoise": 1,
      "latent_image": ["5", 0],
      "model": ["4", 0],
      "negative": ["7", 0],
      "positive": ["6", 0],
      "sampler_name": "euler",
      "scheduler": "normal",
      "seed": 8566257,
      "steps": 20
    }
  },
  "4": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
  },
  "5": {
    "class_type": "EmptyLatentImage",
    "inputs": {"batch_size": 1, "height": 512, "width": 512}
  },
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": {"clip": ["4", 1], "text": "masterpiece best quality girl"}
  },
  "7": {
    "class_type": "CLIPTextEncode",
    "inputs": {"clip": ["4", 1], "text": "bad hands"}
  },
  "8": {
    "class_type": "VAEDecode",
    "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
  },
  "9": {
    "class_type": "SaveImage",
    "inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]}
  }
}
```

Submission is always `{"prompt": <that dict>}` POSTed as JSON to `/prompt`. The body shape is demonstrated in `script_examples/basic_api_example.py:98-110`.

## CLI commands (this skill)

- `comfyui workflow run FILE.json` — submit an API workflow to `/prompt`. If the file is UI format, fail with the re-export instructions from above.
- `comfyui workflow run IMAGE.png` (or `.webp`) — extract the embedded `prompt` chunk (PNG) or EXIF tag `0x0110` (WebP), then submit.
- `comfyui workflow extract IMAGE.png [--ui | --api | --both]` — dump the embedded workflow(s) to stdout or to a file. Default is `--api` because that's what the user almost always wants. `--both` emits a small envelope `{"api": ..., "ui": ...}`.
- `comfyui workflow validate FILE` — check that it parses, that it's API format (not UI), that every `[node_id, slot]` reference in `inputs` points to an existing node id, and that `class_type` is non-empty. If the server is reachable, cross-check class names against `/object_info`. If UI format, print the re-export instructions and exit non-zero.

## Gotchas

- **Empty `workflow` chunk.** Images generated by submitting directly to `/prompt` (no UI graph behind them) still get a `prompt` chunk, but `extra_pnginfo["workflow"]` is whatever the caller sent — often nothing. Always treat the `workflow` chunk as optional; `prompt` is the reliable one. Source: `extra_pnginfo` is populated by the server from the request's `extra_data`, not synthesized.
- **Custom nodes stripping metadata.** Some third-party `SaveImage` replacements omit `PngInfo` entirely, or honor `--disable-metadata` (`nodes.py:1664`). If `img.info["prompt"]` is missing, you're not going to recover it — tell the user and bail.
- **PNG vs WebP reliability.** PNG text chunks survive most tooling (Pillow, ImageMagick, browsers) untouched. WebP EXIF is less portable — some image editors silently strip EXIF. Prefer PNG as the embedded-metadata medium when the user has a choice.
- **Large `prompt` chunks.** Complex workflows (100+ nodes, lots of LoRAs) easily push the `prompt` JSON above 1 MB. PNG `tEXt` chunks have no size limit, but some readers do. The skill should use `Image.open(...).info[...]` (lazy, streams the file) rather than loading raw PNG bytes into memory.
- **JSON escaping.** The JSON is double-serialized: the chunk text IS a JSON string. `json.loads(img.info["prompt"])` is mandatory — don't treat it as a dict directly.
- **APNG / animated WebP.** Animated PNG uses private `comf` chunks (`_ui.py:98-120`) which Pillow does NOT expose in `img.info`. Animated WebP uses the same EXIF path as static WebP — `save_animated_webp` calls `_create_webp_metadata` (`_ui.py:222`), so the extraction snippet above works unchanged. If extraction silently returns nothing for an animated PNG, that's why — this is a known limitation of the simple Pillow path.
- **`--disable-metadata` CLI flag.** If ComfyUI was launched with `--disable-metadata`, no chunks are written at all (`nodes.py:1664`, `_ui.py:87`). You **cannot** detect `--disable-metadata` from the image alone — a stripped PNG looks identical to one written by a third-party saver that omits metadata. Treat "no `prompt` chunk" as a user error and show: `"No embedded workflow found. Was ComfyUI started with --disable-metadata, or did a custom SaveImage node strip it? Try a different image."`

## Sources

Code:

- `E:\workspaces\tools\comfy\ComfyUI\nodes.py:19` — `from PIL.PngImagePlugin import PngInfo`
- `E:\workspaces\tools\comfy\ComfyUI\nodes.py:1656-1674` — `SaveImage.save_images`, the canonical PNG metadata writer (`prompt` chunk + each `extra_pnginfo` key)
- `E:\workspaces\tools\comfy\ComfyUI\nodes.py:1664` — `args.disable_metadata` gate
- `E:\workspaces\tools\comfy\ComfyUI\nodes.py:479-512` — `SaveLatent` writes `.latent` binary files (custom `PrmT` header), NOT PNGs. Pillow cannot extract from these — they use a different pathway and are outside this page's scope.
- `E:\workspaces\tools\comfy\ComfyUI\comfy_api\latest\_ui.py:85-95` — `ImageSaveHelper._create_png_metadata` (v3 nodes, same chunk names)
- `E:\workspaces\tools\comfy\ComfyUI\comfy_api\latest\_ui.py:98-120` — `_create_animated_png_metadata` (APNG uses private `comf` chunks)
- `E:\workspaces\tools\comfy\ComfyUI\comfy_api\latest\_ui.py:122-135` — `_create_webp_metadata` (EXIF `0x0110` for `prompt`, descending from `0x010F` for `extra_pnginfo`)
- `E:\workspaces\tools\comfy\ComfyUI\comfy_execution\jobs.py:103-104` — server reads `extra_pnginfo` back out (`extra_pnginfo.get('workflow', {}).get('id')`) — confirms the UI-format key really is `workflow`
- `E:\workspaces\tools\comfy\ComfyUI\script_examples\basic_api_example.py` — canonical API-format workflow and `/prompt` submission wrapper (`{"prompt": <workflow>}`)
- `E:\workspaces\tools\comfy\ComfyUI\comfy_extras\nodes_images.py:498-512` — confirms the same pattern (`IO.Hidden.prompt` + iterate `extra_pnginfo`) in the v3 image nodes

Docs and references:

- ComfyUI examples (load any example and view its raw `.json` in the browser): <https://comfyanonymous.github.io/ComfyUI_examples/>
- ComfyUI interface settings (for the "Enable Dev mode Options" toggle): <https://docs.comfy.org/interface/settings>
- Pillow PNG format docs (tEXt chunks, pnginfo): <https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#png>
- Pillow EXIF access (`Image.getexif()`, used for WebP): <https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.Image.Image.getexif>
- ComfyUI_frontend `graphToPrompt` — upstream source of UI → API conversion, not present in this Python tree: <https://github.com/Comfy-Org/ComfyUI_frontend>

Related: the canonical workflow JSON schema spec lives at <https://docs.comfy.org/specs/workflow_json>. The `interface/settings` page above is the live official doc for the Dev mode toggle.
