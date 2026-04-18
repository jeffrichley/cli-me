---
title: ComfyUI Queue API
description: REST endpoints for submitting workflows, inspecting the queue, and retrieving outputs.
---

## Overview

ComfyUI exposes an unauthenticated HTTP API over aiohttp for driving the generation queue. Submit workflows with `POST /prompt`, inspect the queue with `GET /queue`, fetch results with `GET /history/<prompt_id>`, and abort execution with `POST /interrupt`. This page is the source of truth for what each endpoint actually accepts and returns, grounded in `server.py`.

Every route below is ALSO served at `/api/<path>`. The server loops over its own route table and re-registers each non-static route under the `/api` prefix for frontend dev-server proxying (`server.py:1057-1063`). `POST /prompt` and `POST /api/prompt` hit the same handler.

## Endpoints reference table

| Method | Path                        | Purpose                                                   | Auth |
|--------|-----------------------------|-----------------------------------------------------------|------|
| POST   | `/prompt`                   | Submit a workflow to the queue                            | none |
| GET    | `/prompt`                   | Get exec info (nested: `{"exec_info": {"queue_remaining": N}}`) | none |
| GET    | `/queue`                    | List running and pending queue items                      | none |
| POST   | `/queue`                    | Clear queue or delete specific items                      | none |
| POST   | `/interrupt`                | Interrupt the currently running prompt                    | none |
| POST   | `/free`                     | Signal PromptQueue to unload models / free memory on next idle | none |
| GET    | `/history`                  | List completed prompts with outputs                       | none |
| GET    | `/history/{prompt_id}`      | Fetch one completed prompt with outputs                   | none |
| POST   | `/history`                  | Clear history or delete specific history items            | none |

There is no auth layer on these routes. Anyone who can reach the host and port can submit workflows.

## POST /prompt

Submit a workflow for execution. See `server.py:915-968`.

Request body:

```json
{
  "client_id": "optional-stable-client-id",
  "prompt": {
    "3": {
      "class_type": "KSampler",
      "inputs": { "seed": 5, "steps": 20, "cfg": 8, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0] }
    }
  },
  "extra_data": { "foo": "bar" },
  "front": false,
  "number": 0,
  "prompt_id": "optional-uuid-to-override",
  "partial_execution_targets": null
}
```

Only `prompt` is required. `prompt` is the API-format workflow (node_id -> {class_type, inputs}). `client_id` is echoed into `extra_data` and drives WebSocket event routing. `front: true` enqueues ahead of existing pending items by negating the sort key (`server.py:925-927`). `prompt_id` defaults to a fresh UUID if omitted (`server.py:933`). On valid submit the server also injects `extra_data.create_time` as a millisecond-precision Unix timestamp (`server.py:954`), so the queue/history echo will contain `create_time` even when the request body did not. Before validation, the JSON body is also passed through `self.trigger_on_prompt(json_data)` (`server.py:919`, handler at `server.py:1268`) — external hooks can mutate the submitted payload, so the echo in `/queue` and `/history` may differ from what the client sent.

Success response (HTTP 200):

```json
{
  "prompt_id": "9c6f...-uuid",
  "number": 3,
  "node_errors": {}
}
```

Validation-error response (HTTP 400, not 422):

```json
{
  "error": {
    "type": "prompt_outputs_failed_validation",
    "message": "Prompt outputs failed validation",
    "details": "...",
    "extra_info": {}
  },
  "node_errors": {
    "3": {
      "errors": [ { "type": "...", "message": "...", "details": "...", "extra_info": {} } ],
      "dependent_outputs": ["9"],
      "class_type": "KSampler"
    }
  }
}
```

Missing-prompt response (HTTP 400):

```json
{ "error": { "type": "no_prompt", "message": "No prompt provided", "details": "No prompt provided", "extra_info": {} }, "node_errors": {} }
```

curl example:

```bash
curl -sS -X POST http://127.0.0.1:8188/prompt \
  -H "Content-Type: application/json" \
  -d @workflow_api.json
```

Python httpx example:

```python
import httpx, uuid, json

with open("workflow_api.json") as f:
    workflow = json.load(f)

payload = {
    "client_id": str(uuid.uuid4()),
    "prompt": workflow,
}

r = httpx.post("http://127.0.0.1:8188/prompt", json=payload, timeout=30.0)
r.raise_for_status()
data = r.json()
print(data["prompt_id"], data["number"])
```

## GET /queue

Snapshot of the queue. See `server.py:907-913`.

Response:

```json
{
  "queue_running": [
    [0.0, "prompt-uuid-1", { "3": { "class_type": "KSampler", "inputs": {} } }, { "client_id": "...", "create_time": 1700000000000 }, ["9"]]
  ],
  "queue_pending": [
    [1.0, "prompt-uuid-2", { "...": "..." }, { "client_id": "..." }, ["9"]]
  ]
}
```

Each item is a 5-tuple `[number, prompt_id, prompt, extra_data, outputs_to_execute]`. The 6th tuple slot (`sensitive`) is stripped server-side by `_remove_sensitive_from_queue` at `server.py:57-59`.

## POST /queue

Mutate the pending queue. See `server.py:970-982`.

Clear all pending items:

```json
{ "clear": true }
```

Delete specific pending items by `prompt_id`:

```json
{ "delete": ["prompt-uuid-1", "prompt-uuid-2"] }
```

Returns HTTP 200 with an empty body on success. `delete` only affects pending items — the running prompt is not popped. Use `POST /interrupt` to stop the running prompt.

## POST /interrupt

Interrupt execution. See `server.py:984-1014`.

Request body (any of these work):

```json
{}
```

```json
{ "prompt_id": "prompt-uuid-1" }
```

With no body or no `prompt_id`, it calls a global `nodes.interrupt_processing()` (`server.py:1010-1012`). With a `prompt_id`, it only interrupts if that id matches a currently running prompt; otherwise it is a no-op and logs a message (`server.py:993-1008`).

Returns HTTP 200 with an empty body. `/interrupt` only affects the RUNNING prompt. Pending items keep going after the running one is cancelled — you must combine it with `POST /queue {"delete": [...]}` to stop a pending prompt.

## POST /free

Tell the PromptQueue to unload models and/or release GPU memory the next time it goes idle. See `server.py:1016-1025`.

Request body:

```json
{ "unload_models": true, "free_memory": true }
```

Both keys are optional booleans and default to `false`. `unload_models: true` sets the queue's `unload_models` flag; `free_memory: true` sets the `free_memory` flag (`server.py:1021-1024`). The flags are consumed on the next idle tick of the executor, so the call returns immediately — it does NOT block until memory is reclaimed. Returns HTTP 200 with an empty body.

curl example:

```bash
curl -sS -X POST http://127.0.0.1:8188/free \
  -H "Content-Type: application/json" \
  -d '{"unload_models": true, "free_memory": true}'
```

## GET /history and GET /history/{prompt_id}

Fetch completed prompt records. See `server.py:888-905` and `execution.py:1282-1307`.

`GET /history` accepts optional query params `max_items` and `offset`. Default returns the full history dict.

`GET /history/{prompt_id}` returns a single-entry dict (or `{}` if the id is unknown).

Response shape (keyed by `prompt_id`):

```json
{
  "9c6f...-uuid": {
    "prompt": [0.0, "9c6f...-uuid", { "3": { "class_type": "KSampler", "inputs": {} } }, { "client_id": "...", "create_time": 1700000000000 }, ["9"], {}],
    "outputs": {
      "9": {
        "images": [ { "filename": "ComfyUI_00001_.png", "subfolder": "", "type": "output" } ]
      }
    },
    "status": {
      "status_str": "success",
      "completed": true,
      "messages": [ ["execution_start", { "prompt_id": "9c6f...-uuid", "timestamp": 1700000000000 }] ]
    },
    "meta": {
      "9": { "node_id": "9", "display_node": "9", "parent_node": null, "real_node_id": "9" }
    }
  }
}
```

Unlike `/queue`, `/history` does NOT strip the 6th tuple slot. The stored record retains the full 6-tuple `(number, prompt_id, prompt, extra_data, outputs_to_execute, sensitive)` because `PromptQueue.task_done` writes the raw queue item back into history (`execution.py:1237-1238`). Slot 5 (`sensitive`) is an object that may contain relocated `api_key_comfy_org` / `auth_token_comfy_org` values — treat this field as a secret surface. `entry["prompt"][2]` is still the submitted workflow dict (safe index).

`status.status_str` is `"success"` or `"error"`. `status.completed` is a bool. `status.messages` is a list of `[event_name, payload]` pairs recorded during execution. Possible event names include `execution_start` (`execution.py:724`), `execution_cached` (`execution.py:751`), `execution_success` (`execution.py:795`), `execution_error` (`execution.py:695`), and `execution_interrupted` (`execution.py:682`) — any of these may appear in the list. The `outputs` dict is keyed by node_id; `images`/`gifs`/`latents`/`audio` keys are contributed by individual output nodes (e.g. `SaveImage` writes `{"ui": {"images": results}}` at `nodes.py:1682`).

History is capped at 10000 entries by `MAXIMUM_HISTORY_SIZE = 10000` in `execution.py:1186`. Once a 10001st entry is added, the oldest is evicted FIFO (`execution.py:1227-1228`). Long-running servers will lose old prompt results unless you persist them.

## POST /history

Mutate history. See `server.py:1027-1038`.

Clear all history:

```json
{ "clear": true }
```

Delete specific entries:

```json
{ "delete": ["prompt-uuid-1", "prompt-uuid-2"] }
```

Returns HTTP 200 with an empty body.

## CLI Commands

The `comfyui-cli` CLI implements this mapping (run via `uv run comfyui_cli.py <cmd>` from the skill's `scripts/` directory):

| Command                                 | Endpoint                                 |
|-----------------------------------------|------------------------------------------|
| `comfyui queue submit FILE`             | `POST /prompt` with FILE as the workflow |
| `comfyui queue list`                    | `GET /queue`                             |
| `comfyui queue status [PROMPT_ID]`      | `GET /queue` (no id) or `GET /history/<id>` |
| `comfyui queue wait PROMPT_ID`          | Poll `GET /history/<id>` (optional `--live` via WebSocket) |
| `comfyui queue cancel PROMPT_ID`        | `POST /queue {"delete":[...]}` + `POST /interrupt` |
| `comfyui queue clear`                   | `POST /queue {"clear": true}`            |
| `comfyui queue clear-history`           | `POST /history {"clear": true}`          |

`wait` polls `/history/<id>` until the entry appears, but the entry appearing means completed, NOT successful. Once present, `wait` must read `entry["status"]["status_str"]` and treat anything other than `"success"` as failure (exit non-zero). Possible non-success outcomes include execution errors and interrupted prompts — `status.messages` can include `execution_error` (`execution.py:695`) or `execution_interrupted` (`execution.py:682`) in those cases. `cancel` first tries to delete from the pending queue; if that fails, it interrupts.

## Gotchas

1. **No `--max-queue-size` flag exists.** Despite claims elsewhere, `server.py` and `comfy/cli_args.py` contain no such option. `PromptQueue.queue` is a plain heap-backed list with no `maxsize` (`execution.py:1194`, `1199-1203`). `POST /prompt` never returns 503 from queue pressure — validation failures return 400, not 422, and missing `prompt` returns 400 (`server.py:960, 968`).
2. **`/interrupt` only stops the RUNNING prompt.** Pending prompts will execute in sequence after the interrupt. To cancel pending work, call `POST /queue {"delete": [...]}`. To cancel everything, combine `POST /queue {"clear": true}` with `POST /interrupt`.
3. **A 200 from `POST /prompt` is not a success guarantee.** It only means the workflow queued. Per-node validation errors are returned inside `node_errors` even on the success branch (`server.py:956`). Node execution can still fail at runtime — check `status.status_str == "success"` in the corresponding history entry before trusting outputs.
4. **`GET /queue` strips the 6th tuple element.** Each queue item is really a 6-tuple `(number, prompt_id, prompt, extra_data, outputs_to_execute, sensitive)` but `_remove_sensitive_from_queue` truncates to 5 (`server.py:57-59`). Do not rely on the sensitive slot over the wire. `GET /history` does NOT strip it — history entries echo the full 6-tuple (`execution.py:1237-1238`).
5. **History is capped at 10000 entries.** Once the 10001st entry is added, the oldest is evicted FIFO (`execution.py:1186, 1227-1228`). Long-running servers will lose old prompt results unless you persist them.
6. **`api_key_comfy_org` and `auth_token_comfy_org` are silently relocated.** If your request body's `extra_data` includes either key (defined as `SENSITIVE_EXTRA_DATA_KEYS = ("auth_token_comfy_org", "api_key_comfy_org")` in `execution.py:151`), the server pops them out of `extra_data` before queuing and stores them in a separate sensitive slot (`server.py:951-953`). They do NOT round-trip through `/queue`, and in `/history` they only appear in the 6th tuple element — never in `extra_data` itself.
7. **Duplicate `prompt_id` silently overwrites history.** Prompt IDs are NOT deduplicated by the server. Submitting two prompts with the same `prompt_id` creates two independent queue entries; whichever finishes second overwrites the first at `self.history[prompt[1]] = {...}` (`execution.py:1237`). If you explicitly set `prompt_id`, ensure it is unique — the default server-generated UUID (`server.py:933`) is safe.
8. **JSON-parse error asymmetry across POST handlers.** `POST /prompt` (`server.py:918`), `POST /queue` (`server.py:972`), `POST /history` (`server.py:1029`), and `POST /free` (`server.py:1018`) call `await request.json()` without a try/except — an invalid JSON body surfaces as an aiohttp 500-class error. `POST /interrupt` is the exception: it catches `json.JSONDecodeError` and treats the body as `{}` (`server.py:986-989`). Always submit well-formed JSON and treat any 500 from these routes as "malformed request".

## Sources

- `E:\workspaces\tools\comfy\ComfyUI\server.py:57-59` — `_remove_sensitive_from_queue`
- `E:\workspaces\tools\comfy\ComfyUI\server.py:691-693` — `GET /prompt`
- `E:\workspaces\tools\comfy\ComfyUI\server.py:888-900` — `GET /history`
- `E:\workspaces\tools\comfy\ComfyUI\server.py:902-905` — `GET /history/{prompt_id}`
- `E:\workspaces\tools\comfy\ComfyUI\server.py:907-913` — `GET /queue`
- `E:\workspaces\tools\comfy\ComfyUI\server.py:915-968` — `POST /prompt`
- `E:\workspaces\tools\comfy\ComfyUI\server.py:970-982` — `POST /queue`
- `E:\workspaces\tools\comfy\ComfyUI\server.py:984-1014` — `POST /interrupt` (JSON-decode guarded)
- `E:\workspaces\tools\comfy\ComfyUI\server.py:1016-1025` — `POST /free`
- `E:\workspaces\tools\comfy\ComfyUI\server.py:1027-1038` — `POST /history`
- `E:\workspaces\tools\comfy\ComfyUI\server.py:1057-1063` — transparent `/api` prefix duplication
- `E:\workspaces\tools\comfy\ComfyUI\server.py:1107-1112` — `get_queue_info` (nested `exec_info`)
- `E:\workspaces\tools\comfy\ComfyUI\server.py:951-954` — sensitive-key relocation + `create_time` injection
- `E:\workspaces\tools\comfy\ComfyUI\server.py:919, 1268` — `trigger_on_prompt` hook
- `E:\workspaces\tools\comfy\ComfyUI\execution.py:151` — `SENSITIVE_EXTRA_DATA_KEYS` tuple
- `E:\workspaces\tools\comfy\ComfyUI\execution.py:1186` — `MAXIMUM_HISTORY_SIZE = 10000`
- `E:\workspaces\tools\comfy\ComfyUI\execution.py:1188-1320` — `PromptQueue` implementation
- `E:\workspaces\tools\comfy\ComfyUI\execution.py:1227-1228` — FIFO history eviction
- `E:\workspaces\tools\comfy\ComfyUI\execution.py:1237-1238` — history stores full 6-tuple; duplicate `prompt_id` overwrites
- `E:\workspaces\tools\comfy\ComfyUI\execution.py:682, 695, 724, 751, 795` — `execution_*` status.messages event names
- `E:\workspaces\tools\comfy\ComfyUI\execution.py:795-805` — `history_result` (outputs + meta)
- `E:\workspaces\tools\comfy\ComfyUI\nodes.py:1682` — `SaveImage` UI contract (`{"ui": {"images": results}}`)
- `E:\workspaces\tools\comfy\ComfyUI\script_examples\basic_api_example.py` — official minimal client
- https://github.com/comfyanonymous/ComfyUI/blob/master/script_examples/basic_api_example.py — same file on GitHub
- https://github.com/comfyanonymous/ComfyUI — official repo
- https://docs.comfy.org/development/comfyui-server/comms_routes — official doc listing the REST endpoints and their purposes
- https://comfyanonymous.github.io/ComfyUI_examples/ — official workflow examples
