# REST API Surface

Every HTTP endpoint exposed by ComfyUI v0.19.0, grouped by concern. Routes are registered on the aiohttp `web.Application` built inside `PromptServer.__init__` (`server.py:202`). After the core routes are registered, `PromptServer.add_routes` (`server.py:1044`) duplicates every non-static route under an additional `/api` prefix (`server.py:1057-1063`), so every path below is reachable at both `/<path>` and `/api/<path>`. Static mounts (`/extensions/...`, `/templates/...`, `/docs`, `/`) are frontend-only and not documented here.

## Root / frontend

### `GET /`

Serves the ComfyUI frontend's `index.html` with no-cache headers. Not useful for programmatic clients.

- `server.py:316-322`

## Workflow execution

### `POST /prompt`

Queue a workflow for execution. This is the primary write endpoint for the CLI wrapper.

Request body:

```json
{
  "prompt": { "<node_id>": { "class_type": "KSampler", "inputs": {...} }, ... },
  "prompt_id": "optional-uuid-string",
  "number": 0,
  "front": false,
  "client_id": "optional-ws-client-id",
  "extra_data": { "extra_pnginfo": {...} },
  "partial_execution_targets": ["<node_id>", ...]
}
```

Response on success (200):

```json
{ "prompt_id": "uuid", "number": 0, "node_errors": {} }
```

Response on validation failure (400):

```json
{ "error": { "type": "...", "message": "...", "details": "...", "extra_info": {} }, "node_errors": {"<node_id>": {...}} }
```

- `server.py:915-968`
- Uses `execution.validate_prompt` (`execution.py:1065`) then `PromptQueue.put` (`execution.py:1199`).
- `SENSITIVE_EXTRA_DATA_KEYS = ("auth_token_comfy_org", "api_key_comfy_org")` are stripped from `extra_data` before storage (`execution.py:151`, referenced `server.py:951-953`).

### `GET /prompt`

Returns queue summary. Shape: `{"exec_info": {"queue_remaining": <int>}}` — built by `PromptServer.get_queue_info` (`server.py:1107-1112`).

- `server.py:691-693`

### `POST /interrupt`

Interrupts execution. Body is optional; if `{"prompt_id": "..."}` is supplied it only interrupts when that prompt is currently running, otherwise issues a global interrupt.

- `server.py:984-1014`
- Calls `nodes.interrupt_processing()`.

### `POST /free`

Releases resources. Body:

```json
{ "unload_models": true, "free_memory": true }
```

Sets queue flags read by `prompt_worker` in `main.py:341-352` to unload models / reset the executor cache.

- `server.py:1016-1025`

## Queue management

### `GET /queue`

Returns `{"queue_running": [...], "queue_pending": [...]}`. Each item is a 5-tuple `(number, prompt_id, prompt, extra_data, outputs_to_execute)` with the sensitive 6th element stripped by `_remove_sensitive_from_queue` (`server.py:57-59`).

- `server.py:907-913`

### `POST /queue`

Body:

```json
{ "clear": true, "delete": ["<prompt_id>", ...] }
```

Clears entire pending queue and/or deletes specific pending items. Running items are not affected.

- `server.py:970-982`

## History

### `GET /history`

Query params: `max_items` (int), `offset` (int, default `-1` meaning "last N"). Returns a dict keyed by `prompt_id`:

```json
{
  "<prompt_id>": {
    "prompt": [number, prompt_id, prompt, extra_data, outputs_to_execute],
    "outputs": { "<node_id>": { "images": [{"filename": "...", "subfolder": "...", "type": "output"}] } },
    "meta":    { "<node_id>": { "node_id": "...", "display_node": "...", "parent_node": "...", "real_node_id": "..." } },
    "status":  { "status_str": "success|error", "completed": true, "messages": [...] }
  }
}
```

- `server.py:888-905`
- Storage side: `PromptQueue.get_history` (`execution.py:1282-1307`); `history_result` structure built in `PromptExecutor.execute_async` (`execution.py:797-805`).

### `GET /history/{prompt_id}`

Same shape as above but keyed by a single `prompt_id` (or `{}` if not found).

- `server.py:902-905`

### `POST /history`

Body `{"clear": true}` wipes all history, `{"delete": ["<prompt_id>", ...]}` removes specific entries.

- `server.py:1027-1038`

## Files: view and upload

### `GET /view`

Serves files from ComfyUI's input/output/temp directories. Query params:

- `filename` (required) — basename only, path traversal is blocked (`server.py:524`). May also be a `blake3:<hex>` hash when the assets system is enabled, resolved via `resolve_hash_to_path` (`server.py:510-515`).
- `type` — `output` (default) | `input` | `temp`
- `subfolder` — optional subfolder inside the type dir
- `channel` — `rgba` (default) | `rgb` | `a` (alpha-only)
- `preview` — formatted as `"webp;<quality>"` or `"jpeg;<quality>"` to return a recompressed preview

Security: dangerous MIME types (`text/html`, `text/javascript`, `text/css`, etc.) are forced to `application/octet-stream` to prevent inline execution (`server.py:609-611`).

- `server.py:501-621`

### `GET /view_metadata/{folder_name}`

Reads the `__metadata__` field from a safetensors file header. Query params: `filename` (must end in `.safetensors`).

- `server.py:623-644`

### `POST /upload/image`

Multipart form upload to the input (default), output, or temp directory. Form fields:

| field       | meaning                                        |
|-------------|------------------------------------------------|
| `image`     | the file (required)                            |
| `type`      | `input` (default) \| `output` \| `temp`         |
| `subfolder` | optional subfolder under the target directory  |
| `overwrite` | `"true"`/`"1"` to overwrite an existing file   |

Response: `{"name": "...", "subfolder": "...", "type": "..."}` (plus an `"asset"` block when `--enable-assets` is set, see `server.py:430-443`). Duplicate detection hashes the incoming bytes against the existing file (`compare_image_hash`, `server.py:370-382`) so uploading the same bytes under the same name is a no-op rather than creating `name (1).png`.

- `server.py:449-452` (route), `server.py:384-447` (shared `image_upload` helper).

### `POST /upload/mask`

Same form-encoding as `/upload/image` plus `original_ref` (JSON string with `filename`, optional `subfolder`, optional `type`). The uploaded image's alpha channel is copied onto the referenced image and saved back as PNG (`server.py:486-497`).

- `server.py:455-499`

## Introspection

### `GET /system_stats`

Returns CPU + GPU memory info and versions:

```json
{
  "system": {
    "os": "win32", "ram_total": ..., "ram_free": ..., "comfyui_version": "0.19.0",
    "required_frontend_version": "...", "installed_templates_version": "...",
    "required_templates_version": "...", "python_version": "...",
    "pytorch_version": "...", "embedded_python": false, "argv": [...]
  },
  "devices": [{"name": "...", "type": "cuda", "index": 0, "vram_total": ..., "vram_free": ..., "torch_vram_total": ..., "torch_vram_free": ...}]
}
```

- `server.py:646-685`

### `GET /features`

Returns feature-flag negotiation data — `feature_flags.get_server_features()`.

- `server.py:687-689`

### `GET /object_info`

Returns the full node catalog — every registered class_type mapped to its INPUT_TYPES, RETURN_TYPES, category, etc. The shape of one entry is built by the inner `node_info` helper (`server.py:695-742`). Fields include `input`, `input_order`, `output`, `output_name`, `output_is_list`, `name`, `display_name`, `description`, `python_module`, `category`, `output_node`, `deprecated`, `experimental`, `api_node`, `search_aliases`.

- `server.py:744-755`

### `GET /object_info/{node_class}`

Same shape but for a single node class (or `{}` if unknown).

- `server.py:757-763`

### `GET /embeddings`

Returns a list of embedding names (stem only, no extension) resolved via `folder_paths.get_filename_list("embeddings")`.

- `server.py:324-327`

### `GET /extensions`

Returns the list of frontend-extension JS URLs (relative paths) discovered under the web root and under `EXTENSION_WEB_DIRS`. Used by the frontend to bootstrap custom-node UI; not useful for headless clients.

- `server.py:343-355`

### `GET /models`

Returns the list of model folder keys (`["checkpoints", "loras", "vae", ...]`) — just the keys of `folder_paths.folder_names_and_paths`, not the model files themselves.

- `server.py:329-333`

### `GET /models/{folder}`

Returns the list of model filenames in a specific folder via `folder_paths.get_filename_list(folder)`. Returns `404` for unknown folder names.

- `server.py:335-341`

## Job API (jobs feed)

### `GET /api/jobs`

Unified view of running + queued + historical prompts as "jobs". Query params: `status` (comma-separated: `pending`, `in_progress`, `completed`, `failed`), `workflow_id`, `sort_by` (`created_at` | `execution_duration`), `sort_order` (`asc` | `desc`), `limit`, `offset`.

Response shape:

```json
{ "jobs": [...], "pagination": {"offset": 0, "limit": 10, "total": 42, "has_more": true} }
```

- `server.py:765-861`
- Built by `comfy_execution.jobs.get_all_jobs`.

### `GET /api/jobs/{job_id}`

Returns a single job or 404.

- `server.py:863-886`

## WebSocket

### `GET /ws`

Upgrade to a WebSocket. Query param `clientId` lets a client reconnect and reclaim its existing session (dropping the server's old socket for that `sid`). If omitted, the server mints a new UUID hex and sends it back in the initial `status` message. See `websocket-events.md` for the event protocol.

- `server.py:256-314`

## Internal routes (subapp `/internal`)

Mounted via `self.app.add_subapp('/internal', self.internal_routes.get_app())` in `server.py:1050`. Frontend-only, documented here for completeness.

- `GET  /internal/logs` — newline-joined log string (`api_server/routes/internal/internal_routes.py:22-24`).
- `GET  /internal/logs/raw` — `{"entries": [...], "size": {"cols": N, "rows": N}}` (`:26-32`).
- `PATCH /internal/logs/subscribe` — subscribe a WebSocket clientId to live log push (`:34-44`).
- `GET  /internal/folder_paths` — mapping of `folder_name` -> list of registered paths (`:47-52`).
- `GET  /internal/files/{directory_type}` — list files in `input` | `output` | `temp` sorted by newest mtime (`:54-70`).

## Manager subsystem routes

Added by the five managers registered in `PromptServer.add_routes` (`server.py:1045-1049`). Paths listed; see each manager for shape details.

- `app/user_manager.py`: `GET /users`, `POST /users`, `GET /userdata`, `GET /v2/userdata`, `GET /userdata/{file}`, `POST /userdata/{file}`, `DELETE /userdata/{file}`, `POST /userdata/{file}/move/{dest}`.
- `app/model_manager.py`: `GET /experiment/models`, `GET /experiment/models/{folder}`, `GET /experiment/models/preview/{folder}/{path_index}/{filename:.*}`.
- `app/custom_node_manager.py`: `GET /workflow_templates`, `GET /i18n`.
- `app/subgraph_manager.py`: `GET /global_subgraphs`, `GET /global_subgraphs/{id}`.
- `app/node_replace_manager.py`: `GET /node_replacements`.

## Assets API (requires `--enable-assets`)

Mounted by `register_assets_routes` (`app/assets/api/routes.py:87-95`) and then gated at call-time by `_require_assets_feature_enabled` (`:49-60`) which returns `503 SERVICE_DISABLED` if assets weren't enabled. All paths are `/api`-prefixed natively (not via the auto-prefixer).

- `HEAD   /api/assets/hash/{hash}` — 200 if the blake3 hash exists, else 404 (`:182-193`).
- `GET    /api/assets` — paginated list with tag / metadata / name filters (`:196-231`).
- `GET    /api/assets/{id}` — asset detail JSON (`:234-266`).
- `GET    /api/assets/{id}/content` — streamed file download with `?disposition=inline|attachment` (`:269-332`).
- `POST   /api/assets/from-hash` — create a reference to existing content by hash (`:335-372`).
- `POST   /api/assets` — multipart upload (`:375-475`).
- `PUT    /api/assets/{id}` — update name/metadata/preview (`:478-513`).
- `DELETE /api/assets/{id}?delete_content=true` — delete reference, optionally orphan content (`:516-545`).
- `GET    /api/tags` — paginated tag listing (`:548-582`).
- `POST   /api/assets/{id}/tags` — add tags (`:585-630`).
- `DELETE /api/assets/{id}/tags` — remove tags (`:633-677`).
- `GET    /api/assets/tags/refine` — tag histogram for a filtered asset subset (`:680-699`).
- `POST   /api/assets/seed` — start background scan of models/input/output (`:702-749`).
- `GET    /api/assets/seed/status` — scan status (`:752-771`).
- `POST   /api/assets/seed/cancel` — cancel in-progress scan (`:774-781`).
- `POST   /api/assets/prune` — mark-missing sweep (`:784-804`).

## Surprises

- **Every route is served at two paths.** `PromptServer.add_routes` transparently duplicates the routes table under `/api/...` (`server.py:1057-1063`). So e.g. `GET /prompt` and `GET /api/prompt` are the same handler. Most third-party Python clients (e.g. `comfy-api-simplified`) use the unprefixed form; the official frontend uses the `/api/` form.
- **`GET /prompt`** is the queue-depth probe, `POST /prompt` is the submit call — same URL, totally different semantics.
- **`GET /models`** returns folder *keys*, not files. To list actual files you must call `GET /models/{folder}`. This is easy to miss: the natural "list all models" request returns a list of strings that look like categories.
- **`/view` accepts blake3 hashes** as the `filename` query param (`server.py:510-515`) when the assets system is enabled. This is undocumented in any widely-known API doc and lets litegraph reference files by content-hash directly.
- **`/upload/image`** silently dedupes by content hash when a duplicate name is uploaded (`server.py:414`); it does not create `name (1).png` for identical content, only for name collisions with *different* content.
- **Origin guard is on by default.** When `--enable-cors-header` is *not* set, the server installs `create_origin_only_middleware` (`server.py:146-184`, registered `server.py:226`) which rejects cross-site requests to loopback addresses with 403. Headless clients running in the same origin are fine; anything talking to a remote ComfyUI will need `--enable-cors-header` or to spoof `Host`/`Origin`.
- **Asset routes require a server flag.** Endpoints under `/api/assets/*` return `503 SERVICE_DISABLED` unless ComfyUI was started with `--enable-assets`, even though the routes are always registered (`app/assets/api/routes.py:49-60`).
