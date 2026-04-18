# Key Functions

The handful of Python callables a CLI wrapper for ComfyUI v0.19.0 actually needs to reason about. Each entry cites the file and first line of the definition so you can jump straight to the source.

## Server lifecycle and routing

### `PromptServer.__init__`
- `server.py:203-254`
- Builds the aiohttp `web.Application`, installs middlewares (cache-control, deprecation warning, optional compression, CORS **or** origin-guard, optional block-external, optional manager), constructs the five app-level managers (`UserManager`, `ModelFileManager`, `CustomNodeManager`, `SubgraphManager`, `NodeReplaceManager`), wires the `PromptQueue`, and registers every inline route shown in `api-surface.md` directly against `self.routes`.

### `PromptServer.add_routes`
- `server.py:1044-1105`
- Attaches the manager sub-routes, auto-duplicates every non-static route under `/api/<path>`, mounts `/internal`, mounts `/extensions/<pkg>`, `/templates`, `/docs`, and the web root. The CLI wrapper calls this indirectly via `main.py:478`.

### `PromptServer.send` and `PromptServer.send_sync`
- `server.py:1114-1124` (async dispatcher), `server.py:1216-1218` (thread-safe enqueue)
- `send_sync(event, data, sid=None)` is the single broadcast entry point used by every background thread to push a WebSocket message; it hands the tuple to `self.messages` and `publish_loop` (`server.py:1223-1226`) drains it and calls `send` on the event loop thread.

## Workflow execution

### `execution.PromptExecutor.execute` / `execute_async`
- `execution.py:710-811`
- The inner event loop. Sets `server.client_id` from `extra_data`, emits `execution_start`, `execution_cached`, runs nodes through `ExecutionList`, records `self.history_result = {"outputs": ..., "meta": ...}`, and emits `execution_success` / `execution_error` / `execution_interrupted`. `execute` is a synchronous wrapper (`execution.py:710-711`) that runs `execute_async` via `asyncio.run`; this is what `prompt_worker` calls.

### `execution.validate_prompt`
- `execution.py:1065-1184`
- Returns `(ok, error_or_none, list_of_output_node_ids, node_errors_dict)`. Called from `POST /prompt` (`server.py:941`) before the queue `put`. A wrapper that mirrors client-side validation should use the same `(ok, error, outputs, node_errors)` tuple shape.

### `execution.PromptQueue.put` / `get` / `task_done`
- `execution.py:1199-1203` (put), `execution.py:1205-1216` (get), `execution.py:1223-1243` (task_done)
- Min-heap priority queue keyed by the tuple's first element (the `number` from the prompt submission). `put` notifies `self.not_empty`; `get(timeout)` blocks and returns `(item, int_task_id)`; `task_done` moves the running item into `self.history` with its `ExecutionStatus`.

## Queue / history introspection

### `PromptQueue.get_current_queue_volatile`
- `execution.py:1254-1258`
- Returns `(running_list, queued_copy)` — safe for read-only queue snapshots. Backs `GET /queue` and the jobs API.

### `PromptQueue.get_history`
- `execution.py:1282-1307`
- Returns the stored `{prompt_id: {...}}` history dict with support for `prompt_id` / `max_items` / `offset` filtering. Backs `GET /history` and `GET /history/{prompt_id}`.

## Filesystem resolution

### `folder_paths.get_folder_paths`
- `folder_paths.py:299-301`
- Returns a copy of the list of directories registered under `folder_name` (e.g. `"checkpoints"`, `"loras"`). The source-of-truth dict is `folder_names_and_paths` (`folder_paths.py:14`), seeded by the block at `folder_paths.py:23-53` and extended by `add_model_folder_path` (`:281-297`) and by `extra_model_paths.yaml` via `utils.extra_config.load_extra_path_config` (invoked from `main.py:98-103`).

### `folder_paths.get_filename_list`
- `folder_paths.py:418-426`
- Returns the (cached, mtime-keyed) list of filenames under `folder_name`. The cache is populated by `get_filename_list_` (`:379-390`) and validated by `cached_filename_list_` (`:392-416`). Backs `GET /models/{folder}` and `GET /embeddings`.

## Route handlers worth knowing

### `view_image` handler (`GET /view`)
- `server.py:501-621`
- Resolves a filename or `blake3:<hex>` hash to an absolute path, enforces path-traversal protection (`:524`), supports `channel=rgb|rgba|a`, supports `preview=webp;<q>`/`jpeg;<q>` for on-the-fly re-encoded previews, and forces dangerous mimetypes to octet-stream. A wrapper's "download output" operation lives here.

### `image_upload` helper and `POST /upload/image`
- `server.py:384-447` (helper), `server.py:449-452` (route)
- Accepts multipart form fields `image`, `type`, `subfolder`, `overwrite`. Writes into `input`/`output`/`temp`, dedupes by content hash on name collision (`compare_image_hash`, `:370-382`), and returns `{"name": "...", "subfolder": "...", "type": "..."}` (plus an `"asset"` block when `--enable-assets` is on).

### `post_prompt` handler (`POST /prompt`)
- `server.py:915-968`
- The only public write path into the executor. Accepts `prompt`, optional `prompt_id`, optional `client_id` (routed into `extra_data["client_id"]` so WebSocket events target that sid), optional `number`/`front` for priority, optional `partial_execution_targets`. Calls `validate_prompt`, then `self.prompt_queue.put((number, prompt_id, prompt, extra_data, outputs_to_execute, sensitive))`.

### `prompt_worker` (background thread target)
- `main.py:276-365`
- The loop that pulls from the queue, calls `PromptExecutor.execute`, then `PromptQueue.task_done`, then sends the final `executing {"node": null, ...}` sentinel (`main.py:324-325`), then handles `unload_models`/`free_memory` flags and GC. Started as a daemon thread in `main.py:481`.

## Surprises

- **`send_sync` is the *only* threadsafe send path.** Anything that isn't the aiohttp event loop thread must use `send_sync`, never `send`. `hijack_progress` (`main.py:376-405`) and `PromptExecutor.add_message` (`execution.py:660-667`) both obey this; a wrapper that tries to push WS events from a worker thread must too.
- **`add_message` is what attaches `timestamp` to execution events**, not `send_sync` itself. Events that bypass `add_message` (the `executing {"node": null}` sentinel at `main.py:325`, the `ExecutionBlocked` path at `execution.py:525`) don't carry a timestamp.
- **`PromptExecutor.history_result`** is the structured output bundle (`execution.py:802-805`) written into the history by `prompt_worker` via `q.task_done(item_id, e.history_result, status=...)` (`main.py:318-323`). Anything a wrapper wants to return to the user — saved filenames, subfolders, metadata — comes from there.
- **Queue items are 6-tuples** in flight (`number, prompt_id, prompt, extra_data, outputs_to_execute, sensitive`) but the 6th element is stripped before history via `remove_sensitive = lambda prompt: prompt[:5] + prompt[6:]` (`main.py:317`) and before `/queue` responses via `_remove_sensitive_from_queue` (`server.py:57-59`). External consumers only ever see 5-tuples.
