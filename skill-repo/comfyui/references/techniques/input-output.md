---
title: ComfyUI Input/Output Files
description: /upload/image, /view, and output-file resolution via /history.
---

# ComfyUI Input/Output Files

ComfyUI exposes a small, opinionated file-transfer surface over HTTP: one endpoint to push bytes up (`/upload/image`), one to pull bytes down (`/view`), and one structured map (`/history/<id>`) that tells you which file each `SaveImage`-style node produced. The `assets` command group in the CLI is a thin wrapper over exactly these three routes.

## Directory layout

ComfyUI keeps three logical directories, addressed by a `type` string (`input`, `output`, `temp`). The authoritative mapping lives in `folder_paths.get_directory_by_type`:

```python
# folder_paths.py:206-213
def get_directory_by_type(type_name: str) -> str | None:
    if type_name == "output":
        return get_output_directory()
    if type_name == "temp":
        return get_temp_directory()
    if type_name == "input":
        return get_input_directory()
    return None
```

- `input/` — uploads land here by default; `LoadImage` reads from here (`nodes.py:1700-1708`).
- `output/` — `SaveImage` writes here with `type = "output"` (`nodes.py:1627-1679`).
- `temp/` — `PreviewImage` writes here with `type = "temp"` (`nodes.py:1684-1689`); treated as transient.

Any `type` value outside these three returns `None` and the server rejects the request.

## POST /upload/image

Defined at `server.py:449-452`; delegates to `image_upload` at `server.py:384-447`.

Multipart form fields (all via `await request.post()`):

| Field | Required | Values | Source |
|---|---|---|---|
| `image` | yes | the file bytes (multipart file part) | `server.py:385` |
| `type` | no | `input` \| `temp` \| `output` (default `input` via `get_dir_by_type`, `server.py:357-368`) | `server.py:389` |
| `subfolder` | no | relative path inside the type dir (default `""`) | `server.py:397` |
| `overwrite` | no | `"true"` or `"1"` to overwrite; anything else means "rename on collision" | `server.py:386, 409-419` |

Response is JSON:

```json
{"name": "cat (1).png", "subfolder": "refs", "type": "input"}
```

built at `server.py:428`. When `args.enable_assets` is set, an `asset` key with Blake3 hash + size is also attached (`server.py:430-443`).

### curl

```bash
curl -X POST http://127.0.0.1:8188/upload/image \
  -F "image=@./cat.png" \
  -F "type=input" \
  -F "subfolder=refs" \
  -F "overwrite=false"
```

### Python (httpx)

```python
import httpx
from pathlib import Path

path = Path("cat.png")
with path.open("rb") as fh:
    files = {"image": (path.name, fh, "image/png")}
    data = {"type": "input", "subfolder": "refs", "overwrite": "false"}
    r = httpx.post("http://127.0.0.1:8188/upload/image",
                   files=files, data=data, timeout=60.0)
r.raise_for_status()
resp = r.json()  # {"name": ..., "subfolder": ..., "type": ...}
```

## POST /upload/mask

Defined at `server.py:455-499`. Same form fields as `/upload/image`, plus one required field:

- `original_ref` — a JSON string of `{"filename": "...", "subfolder": "...", "type": "..."}` pointing at the image the mask belongs to (`server.py:460-461`).

The server loads the original, copies its PNG metadata, extracts the alpha channel from the uploaded mask, and writes a new RGBA PNG (`server.py:486-497`). Path traversal is explicitly blocked (`server.py:467-468`: rejects absolute paths and `..`).

## GET /view

Defined at `server.py:501-621`. Returns the raw file bytes (or a re-encoded preview).

Query parameters:

| Param | Required | Values | Default | Source |
|---|---|---|---|---|
| `filename` | yes | basename; may be suffixed `[output]`/`[input]`/`[temp]` to force type (`folder_paths.py:243-256`) | — | `server.py:503-504` |
| `subfolder` | no | relative path inside the type dir | `""` | `server.py:534-538` |
| `type` | no | `output` \| `input` \| `temp` | **`output`** (`server.py:528`) | `server.py:527-529` |
| `preview` | no | `<fmt>[;<quality>]`, e.g. `webp;50` or `jpeg;80` | none (serve original) | `server.py:544-562` |
| `channel` | no | `rgba` \| `rgb` \| `a` | `rgba` (`server.py:564-567`) | `server.py:564-599` |

Note the default `type` for `/view` is `output` — the opposite of `/upload/image`, which defaults to `input`. Don't assume symmetry.

`filename=blake3:<hex>` is a separate resolution branch (`server.py:510-515`). When `--enable-assets` is on, the assets subsystem resolves the hash to a filename via `resolve_hash_to_path`; the frontend's `LoadImage` widget uses this for asset-hash references. The skill should pass literal filenames, not hashes — but document that the branch exists so callers know why `filename` values starting with `blake3:` do not behave like normal basenames.

Preview behavior:
- `preview=webp;50` returns a WebP re-encode at quality 50; quality defaults to 90 if omitted (`server.py:551-553`).
- If `preview` is `jpeg` but `channel=a` (alpha), the server overrides back to `webp` since JPEG has no alpha (`server.py:548-549`).
- `channel=rgb` drops alpha and returns a PNG. `channel=a` returns a PNG of just the alpha channel (`server.py:569-599`).

Certain content types (HTML, JS, CSS) are force-downgraded to `application/octet-stream` to prevent XSS through served files (`server.py:610-611`).

### Example: download a history output

```python
import httpx

base = "http://127.0.0.1:8188"
ref = {"filename": "ComfyUI_00001_.png", "subfolder": "", "type": "output"}
r = httpx.get(f"{base}/view", params=ref, timeout=120.0)
r.raise_for_status()
(Path("out") / ref["filename"]).write_bytes(r.content)
```

## Outputs via /history

When a queued prompt finishes, `GET /history/<prompt_id>` (`server.py:902-905`) returns the entry the executor built in `PromptQueue.task_done` (`execution.py:1237-1242`) plus the `history_result` assembled at `execution.py:797-805`.

Shape:

```json
{
  "<prompt_id>": {
    "prompt": [number, "<prompt_id>", { "<node_id>": {"inputs": {...}, "class_type": "..."}}, {}, []],
    "outputs": {
      "<node_id>": {
        "images": [
          {"filename": "ComfyUI_00001_.png", "subfolder": "", "type": "output"}
        ]
      }
    },
    "meta": { "<node_id>": {"node_id": "...", "display_node": "...", "parent_node": null, "real_node_id": "..."} },
    "status": {
      "status_str": "success",
      "completed": true,
      "messages": [["execution_start", {...}], ["execution_success", {...}]]
    }
  }
}
```

The `outputs.<node_id>` dict keys (`images`, `gifs`, etc.) come straight from whatever the node returned under `{"ui": {...}}` in its `save_images`-style function (`nodes.py:1675-1682` for `SaveImage`, producing `{"filename", "subfolder", "type"}` tuples). Core ComfyUI savers (`SavedImages`, `PreviewImage`) emit the `animated` sibling key alongside `images` — a tuple serialized as `[true]` when the saver wrote an animated PNG/WebP (`comfy_api/latest/_ui.py:51-55, ~:400-404`); the `gifs` key comes from custom-node packs like VideoHelperSuite, not from core. Don't hard-code the list of keys; iterate.

To download every output:

```python
history = httpx.get(f"{base}/history/{prompt_id}", timeout=30.0).json()
entry = history[prompt_id]
for node_id, node_out in entry["outputs"].items():
    for key, refs in node_out.items():
        if not isinstance(refs, list):
            continue  # skip non-list values
        # `animated: [true]` is emitted when the saver wrote an animated PNG/WebP —
        # same `images` list, sibling key tells you the first element is animated.
        if key == "animated":
            continue
        for ref in refs:
            if not isinstance(ref, dict) or "filename" not in ref:
                continue
            r = httpx.get(f"{base}/view", params={
                "filename": ref["filename"],
                "subfolder": ref.get("subfolder", ""),
                "type": ref.get("type", "output"),
            }, timeout=120.0)
            r.raise_for_status()
            # write r.content to disk
```

## CLI commands

| Command | Method | Notes |
|---|---|---|
| `comfyui input upload FILE [--subfolder X] [--overwrite]` | POST `/upload/image` | `type=input`. Prints the server's response JSON as-is; callers MUST use `response["name"]`, not the local filename — collision-rename is silent. |
| `comfyui input list [--subfolder X]` | — | See limitation below. |
| `comfyui output download PROMPT_ID [--dir DIR]` | GET `/history/<id>` + `GET /view` per ref | Default `DIR` is `./comfy_outputs/`. Iterates all `list`-valued keys under each node's outputs. Skips scalar keys like `animated`. Writes `<DIR>/<prompt_id>/<filename>` (flat under prompt_id, no node_id nesting — v1 behavior; TODO: consider node_id nesting in v2 when a prompt emits collisions across nodes). |
| `comfyui output show PROMPT_ID` | GET `/history/<id>` | Prints the `outputs` sub-object as JSON; no downloads. |

### Limitation: `input list`

ComfyUI core exposes **no JSON endpoint to list a directory**. `/view` requires a specific `filename`; `/history` only describes finished prompts. The only directory listings in core are baked into node `INPUT_TYPES` (e.g. `LoadImage` at `nodes.py:1703-1704` enumerates the input dir when the server starts), and that listing is neither paginated nor exposed as a JSON route.

Options for the skill:

1. **Document the gap.** `comfyui input list` exits with a clear error explaining the server has no listing route, and points users at the filesystem directly if they have local access.
2. **Local-only fallback.** If the CLI detects it is running on the same host as the server (match `host` against `127.0.0.1`/`localhost` and the `input/` directory is readable), enumerate with `os.listdir`. Otherwise fail with the message from (1).
3. **Custom-node dependency.** Some community nodes add a listing route; the skill should not assume one.

Ship option (2) with a `--local` flag for clarity, and document it as a ComfyUI limitation.

## Gotchas

1. **No remote directory listing.** See above. `/view` is per-file only; there is no `/list` in core. Plan the UX around this.

2. **Silent collision-rename.** With `overwrite=false` (the default), the server appends ` (1)`, ` (2)`, ... to the filename (`server.py:412-419`). It also hashes the file and, on hash match, reuses the existing file rather than making a new copy (`server.py:413-416`). **Always** return the server's `name` field to the caller; the original filename is a lie after collision.

3. **Path traversal is enforced but asymmetrically.** `/upload/image` normalizes `subfolder` with `os.path.normpath` and then verifies `os.path.commonpath((upload_dir, filepath)) == upload_dir` (`server.py:398-402`); any escape returns 400. `/view` rejects filenames starting with `/` or containing `..` outright (`server.py:523-525`) and applies the same `commonpath` check to the computed subfolder path (`server.py:534-538`). Result: `..` in `filename` is banned at `/view` but normalized at `/upload`; both paths still fail the `commonpath` guard. Do **not** rely on the client to sanitize — but also don't send `..` on upload expecting a redirect; it may silently land in a subfolder rather than error.

4. **Type defaults differ between endpoints.** `/upload/image` defaults to `input` (`server.py:358-361`). `/view` defaults to `output` (`server.py:528`). Always pass `type` explicitly in CLI code to avoid confusion.

5. **Multipart uploads buffer in aiohttp's `request.post()`.** `server.py:451` uses `await request.post()`, which loads the whole multipart body into memory before calling `image_upload`. The body size cap is `args.max_upload_size` (default 100 MB per `comfy/cli_args.py:43`), applied via aiohttp's `client_max_size` at `server.py:234-235`. Override with `--max-upload-size <MB>` on server launch. There is no streaming upload API in core, so for files approaching the cap expect commensurate memory pressure on the server.

6. **PNG metadata comes along for free on mask uploads.** `/upload/mask` copies `tEXt` chunks (including `prompt` / `workflow` JSON that `SaveImage` embeds) from the original into the mask output (`server.py:486-497`). Useful for re-inflating a workflow from a mask-only PNG; also a mild information-leak risk if you share mask PNGs widely.

7. **No symlink special-casing.** The server uses `os.path` + `os.makedirs` + `os.path.isfile` without resolving symlinks. If a user drops a symlink into `input/`, `/view` will follow it (via `FileResponse`) and read whatever it points to. Treat the `input/` / `output/` / `temp/` directories as trust boundaries: anyone who can write into them can exfiltrate any file the server process can read, up to the `commonpath` check — which only guards the **written** path, not symlink targets. Recommend documenting this in skill security notes.

8. **`type=<bogus>` triggers a 500.** Passing an unknown `type` to `/upload/image` or `/view` (anything other than `input`/`output`/`temp`) causes `get_dir_by_type` (`server.py:357-368`) to return without binding `type_dir`, raising `UnboundLocalError` and producing a 500. The skill MUST validate `type` client-side against the three allowed values before calling the server.

9. **Concurrent same-filename upload race.** With `overwrite=false`, the rename loop (`server.py:412-419`) is not atomic — two concurrent uploads of `cat.png` can both pass the `os.path.exists` check at line 413 before either writes, and one gets clobbered. Practical mitigation: add a client-side uuid prefix like `{uuid}_cat.png`.

10. **NUL byte in filename returns 500.** Filenames containing `\x00` raise `ValueError` in Python's path machinery before hitting disk. Sanitize client-side.

11. **GET `/view` with no `filename` returns 404 silently.** Missing `filename` query param falls through to `web.Response(status=404)` (`server.py:621`). The skill should always include it; don't rely on a descriptive error.

12. **`args.enable_assets` asset-register failure is swallowed.** When `--enable-assets` is on, `/upload/image` attempts asset registration inside a `try/except` that only logs a warning (`server.py:430-443`). The upload still returns 200 with `{"name", "subfolder", "type"}` even if registration failed — the skill should treat the response's `asset` key as best-effort and not require it.

## Sources

- `server.py:384-452` — upload handler + `/upload/image` route
- `server.py:455-499` — `/upload/mask` route
- `server.py:501-621` — `/view` route, preview and channel handling
- `server.py:888-905` — `/history` routes
- `folder_paths.py:120-130, 206-213` — directory accessors and `get_directory_by_type`
- `folder_paths.py:243-268` — `annotated_filepath` (handles `name [type]` suffix)
- `nodes.py:1627-1689` — `SaveImage` and `PreviewImage` (how `{filename, subfolder, type}` tuples are born)
- `nodes.py:1700-1779` — `LoadImage` (consumes `input/` directory)
- `execution.py:551-560, 797-805` — `ui_outputs` assembly
- `execution.py:1223-1242` — `task_done` merging `history_result` into `self.history[prompt_id]`

Upstream references:
- ComfyUI server: https://github.com/comfyanonymous/ComfyUI/blob/master/server.py
- ComfyUI nodes: https://github.com/comfyanonymous/ComfyUI/blob/master/nodes.py
- ComfyUI execution: https://github.com/comfyanonymous/ComfyUI/blob/master/execution.py
- ComfyUI folder_paths: https://github.com/comfyanonymous/ComfyUI/blob/master/folder_paths.py
