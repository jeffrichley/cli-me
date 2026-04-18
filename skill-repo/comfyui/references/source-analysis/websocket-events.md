# WebSocket Event Protocol

This document describes the `/ws` event stream exposed by ComfyUI v0.19.0. Text-frame events carry JSON with shape `{"type": <event>, "data": <payload>}` (`server.py:1206-1207`); binary frames carry a 4-byte big-endian event type followed by raw bytes (`server.py:1126-1133`, see `protocol.py:2-6`). All fan-out flows through one pump: workers call the thread-safe `PromptServer.send_sync` (`server.py:1216-1218`), which enqueues onto `self.messages`; `PromptServer.publish_loop` (`server.py:1223-1226`) consumes that queue and dispatches through `PromptServer.send` (`server.py:1114-1124`).

## Connecting

```
GET /ws?clientId=<optional-client-id>
```

- If `clientId` is supplied, the server discards any existing socket under that sid and treats this connection as a reconnect (`server.py:261-263`).
- If omitted, the server mints a new `sid = uuid.uuid4().hex` (`server.py:264-265`) and sends it back in the first `status` message.

Two setup messages are sent immediately after upgrade:

1. `status` with the current queue depth and the assigned `sid` (`server.py:274`).
2. Optionally `executing` echoing the last running node if the client is reclaiming an active session (`server.py:276-277`).

Clients *may* send one `{"type": "feature_flags", "data": {...}}` text frame as the first inbound message; the server responds with its own `feature_flags` payload (`server.py:286-303`). All subsequent inbound frames are ignored.

## Broadcast semantics

`send_sync(event, data, sid=None)` delivers to a single socket when `sid` is set and to every connected socket when `sid` is `None`. Most execution events are sent *only* to the client that submitted the prompt (`server.client_id`, set from `extra_data["client_id"]` in `execution.py:718-721`). Status/queue updates and interruptions broadcast to everyone.

## Text (JSON) events

Each subsection shows the JSON payload (`data` field) and the source line that builds it.

### `status`

Sent on every queue mutation (via `PromptServer.queue_updated`, `server.py:1220-1221`) and once on connect. Payload:

```json
{
  "status": { "exec_info": { "queue_remaining": <int> } },
  "sid": "<client-uuid>"
}
```

The `sid` field is only included on the initial connect message (`server.py:274`); queue-update broadcasts omit it.

- Build sites: `server.py:274` (connect), `server.py:1221` (queue update).

### `feature_flags`

Server-side feature advertisements, sent in response to a client `feature_flags` inbound message.

```json
{ /* contents of feature_flags.get_server_features() */ }
```

- Build site: `server.py:295-299`.

### `execution_start`

First event for a new prompt. The `PromptExecutor.add_message` helper (`execution.py:660-667`) enriches every execution event with a millisecond `timestamp`, so the full payload is:

```json
{ "prompt_id": "<uuid>", "timestamp": 1713456789000 }
```

- Build site: `execution.py:724`.

### `execution_cached`

Fired once per prompt with the set of nodes whose cached outputs will be reused (skipped).

```json
{ "nodes": ["<node_id>", ...], "prompt_id": "<uuid>", "timestamp": 1713456789000 }
```

- Build site: `execution.py:751-753`.

### `executing`

Fired each time execution transitions to a new node. `node` is `null` after the last node completes to signal the prompt is done (see `main.py:325`).

```json
{ "node": "<node_id_or_null>", "display_node": "<node_id>", "prompt_id": "<uuid>" }
```

- Build sites: `server.py:277` (reconnect replay), `execution.py:485` (node starting), `main.py:325` (prompt completion sentinel — note: no `timestamp` here, this one is sent directly via `send_sync`, not through `add_message`).

### `progress`

Legacy per-sampler progress tick, installed by `hijack_progress` (`main.py:376-405`).

```json
{ "value": <int>, "max": <int>, "prompt_id": "<uuid>", "node": "<node_id>" }
```

- Build site: `main.py:388` (`progress` dict), sent at `main.py:391`.

### `progress_state`

Newer "all nodes at once" progress message emitted by `WebUIProgressHandler` (`comfy_execution/progress.py:185-187`).

```json
{
  "prompt_id": "<uuid>",
  "nodes": {
    "<node_id>": {
      "value": <float>,
      "max":   <float>,
      "state": "running" | "finished" | ...,
      "node_id": "<node_id>",
      "prompt_id": "<uuid>",
      "display_node_id": "<node_id>",
      "parent_node_id":  "<node_id_or_null>",
      "real_node_id":    "<node_id>"
    },
    ...
  }
}
```

- Build site: `comfy_execution/progress.py:165-187`.

### `executed`

Fired when a node produced UI outputs — images, text, numbers, etc. This is the event downstream clients watch for to learn about saved files.

```json
{
  "node": "<node_id>",
  "display_node": "<node_id>",
  "output": { "images": [{"filename": "...", "subfolder": "...", "type": "output"}], ... },
  "prompt_id": "<uuid>"
}
```

- Build sites: `execution.py:423` (cache replay — fires even for cached nodes so the UI sees the saved filenames), `execution.py:562` (fresh execution).

### `execution_error`

Fired on a node-level exception (or an `ExecutionBlocked` block).

```json
{
  "prompt_id":         "<uuid>",
  "node_id":           "<node_id>",
  "node_type":         "<class_type>",
  "executed":          ["<node_id>", ...],
  "exception_message": "...",
  "exception_type":    "...",
  "traceback":         ["..."],
  "current_inputs":    {"input_name": ["stringified", "values"]},
  "current_outputs":   ["<node_id>", ...],
  "timestamp":         1713456789000
}
```

- Build sites: `execution.py:525` (execution-block path — note this one is sent direct via `send_sync` without a `timestamp`), `execution.py:684-695` (main error handler via `add_message`, adds `timestamp` and omits `current_outputs` when coming from an `ExecutionBlocked`).

### `execution_interrupted`

Fired when the user cancels via `/interrupt` while a prompt is running. Broadcasts to all clients (`broadcast=True` at `execution.py:682`).

```json
{
  "prompt_id": "<uuid>",
  "node_id":   "<node_id>",
  "node_type": "<class_type>",
  "executed":  ["<node_id>", ...],
  "timestamp": 1713456789000
}
```

- Build site: `execution.py:676-682`.

### `execution_success`

Fired once at the end of a prompt that completed without error.

```json
{ "prompt_id": "<uuid>", "timestamp": 1713456789000 }
```

- Build site: `execution.py:795`.

### `logs`

Only emitted when a client has subscribed via `PATCH /internal/logs/subscribe`. Payload mirrors `GET /internal/logs/raw`:

```json
{ "entries": [{"t": "...", "m": "..."}], "size": {"cols": 80, "rows": 24} }
```

- Build site: `api_server/services/terminal_service.py:60`.

## Binary events

Sent via `send_bytes` (`server.py:1196-1204`). Every binary frame is `struct.pack(">I", event_type)` followed by raw content.

| id | name                             | payload                                                          |
|----|----------------------------------|------------------------------------------------------------------|
| 1  | `PREVIEW_IMAGE`                  | 4-byte image-format tag (1=JPEG, 2=PNG) + raw image bytes        |
| 2  | `UNENCODED_PREVIEW_IMAGE`        | only used internally as an input to `send_image`; never hits the wire |
| 3  | `TEXT`                           | 4-byte node_id length + node_id bytes + UTF-8 text payload       |
| 4  | `PREVIEW_IMAGE_WITH_METADATA`    | 4-byte json length + UTF-8 JSON metadata + raw image bytes       |

- `protocol.py:2-6` (constants), `server.py:1135-1194` (framing).
- Only `PREVIEW_IMAGE_WITH_METADATA` is sent when the client advertises `supports_preview_metadata` via feature flags (`comfy_execution/progress.py:210-230`); otherwise the legacy `PREVIEW_IMAGE` is emitted (`main.py:393-403`).
- `TEXT` carries arbitrary textual node output (e.g. streaming LLM text); emitted by `PromptServer.send_progress_text` (`server.py:1278-1288`).

## Event lifecycle for one prompt

For a prompt submitted with `client_id=<X>`, the ordering observed on socket `<X>` is:

```
status                  -> on connect + on every queue mutation
execution_start         -> as soon as the worker dequeues the item
execution_cached        -> right after, listing nodes skipped due to cache
executing               -> for each node as it starts
progress / progress_state / PREVIEW_IMAGE* -> interleaved during sampling
executed                -> per node that produced UI outputs
execution_success       -> end-of-prompt on clean run
  OR execution_error    -> on failure
  OR execution_interrupted -> on cancel (broadcast to all clients)
executing {"node": null} -> final sentinel from prompt_worker
```

## Surprises

- **No `execution_end` event.** The end-of-prompt signal is `execution_success` (clean), `execution_error` (failure), `execution_interrupted` (cancel), plus a follow-up `executing` with `"node": null`. Clients that wait only for `execution_success` will miss failed and cancelled prompts — track all four.
- **`execution_interrupted` is the only execution event that broadcasts.** Every other per-prompt event targets `server.client_id` only (`execution.py:660-667` sends with `broadcast=False`, `execution.py:682` sets `broadcast=True`). If your client doesn't attach a `client_id` when submitting, you'll never see `executing`/`executed`/`execution_success` — only the global `status` broadcasts.
- **Two different "executing node=null" signals.** `execution.py:485` fires `executing` for a real node starting; `main.py:325` fires a sentinel `executing` with `node=None` *after* `execution_success`/`execution_error` to mark the worker idle. This sentinel carries `prompt_id` but no `timestamp`, unlike the other execution events.
- **`execution_error` has two build sites with different shapes.** The `ExecutionBlocked` path in `execution.py:511-526` sends directly via `send_sync` without the `timestamp`-enriching `add_message` helper, and it fills `current_inputs: []`/`current_outputs: []`. The main error path (`execution.py:683-695`) uses `add_message` so it gets the `timestamp` and populates both fields properly. Parsers must treat both variants as valid.
- **Per-prompt `timestamp`s are server wall-clock ms** (`int(time.time() * 1000)`, `execution.py:663`), not monotonic. Don't compute durations by subtracting them across a clock adjustment.
