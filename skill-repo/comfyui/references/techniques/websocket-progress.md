---
title: ComfyUI WebSocket Progress
description: Real-time events from /ws — queue status, per-node progress, outputs, errors.
---

# ComfyUI WebSocket Progress

## Overview

ComfyUI exposes a WebSocket endpoint at `GET /ws` that streams **real-time execution events** while a workflow runs. Clients use it to see queue status, per-node execution, per-step sampler progress, output emission (file refs + preview images), and errors — all as they happen.

Compared to polling `/history/{prompt_id}`, the WebSocket gives you:

- **Sub-second latency** on status changes (no polling tax).
- **Per-step progress** from sampler nodes (e.g. KSampler's 20 steps), which never appears in `/history`.
- **Live preview images** as binary frames (latent previews during sampling).
- **Immediate error signals** — `execution_error` fires the instant a node fails, without waiting for the queue entry to land in history.

The WebSocket is the only way to build a responsive CLI progress bar. History is the source of truth for **final** output paths; the WebSocket is the source of truth for **while-it-runs**.

## Connecting

Open a WebSocket to `ws://<host>:<port>/ws?clientId=<uuid>`. The server honors the `clientId` query param verbatim — whatever string you pass becomes the session id (`sid`) for that socket (see `server.py:260`). Pass the **same** string as `client_id` in the JSON body of your `POST /prompt` request, or you will only receive broadcast events (queue status updates and `execution_interrupted`), never the targeted events for *your* prompt (see "Gotchas").

```python
import json
import uuid
import urllib.request
import websocket  # pip install websocket-client

server = "127.0.0.1:8188"
client_id = str(uuid.uuid4())

# 1. Open the WebSocket first — any events that fire before you connect are lost.
ws = websocket.WebSocket()
ws.connect(f"ws://{server}/ws?clientId={client_id}")

# 2. Submit the prompt with the SAME client_id.
payload = {"prompt": workflow_dict, "client_id": client_id}
req = urllib.request.Request(
    f"http://{server}/prompt",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
resp = json.loads(urllib.request.urlopen(req).read())
prompt_id = resp["prompt_id"]

# 3. Stream events until execution completes (see "Complete client pattern").
```

On connect, ComfyUI immediately sends a `status` event containing the generated `sid` (`server.py:274`). If the client reconnects while the same session is still executing a node, the server replays the last `executing` event so the UI can resume (`server.py:276-277`).

## Event reference

All JSON events share the shape `{"type": "<event>", "data": {...}}` — the outer envelope is produced by `send_json` at `server.py:1206-1214`. The tables below document the `data` payload.

| Event type | Trigger | Payload keys | File:line |
| --- | --- | --- | --- |
| `status` | Initial connect and every time `queue_remaining` changes | `status.exec_info.queue_remaining` (int), `sid` (str, connect only) | `server.py:274`, `server.py:1221` |
| `feature_flags` | Server reply after client sends its feature-flags handshake as the first text frame | `supports_preview_metadata` (bool) and other server flags | `server.py:295-299` |
| `execution_start` | First event fired when the executor picks up a prompt | `prompt_id` (str), `timestamp` (int ms) | `execution.py:724` |
| `execution_cached` | Right after `execution_start`; lists nodes skipped due to cache hits | `nodes` (list[str]), `prompt_id` (str), `timestamp` (int ms) | `execution.py:751-753` |
| `executing` | A node begins executing (or `node: null` signals "prompt finished") | `node` (str \| null), `display_node` (str), `prompt_id` (str) | `execution.py:485` (start), `main.py:325` (null / done) |
| `progress` | Per-step updates from sampler nodes (KSampler etc. via `set_progress_bar_global_hook`) | `value` (int), `max` (int), `prompt_id` (str), `node` (str) | `main.py:388-391` |
| `progress_state` | Combined state of all non-pending nodes — fires on every start/update/finish inside the progress registry | `prompt_id` (str), `nodes` (dict[node_id -> {value, max, state, node_id, prompt_id, display_node_id, parent_node_id, real_node_id}]) | `comfy_execution/progress.py:185-187` |
| `executed` | Fires **only** for nodes that produce UI output (SaveImage, PreviewImage, etc.) — cached and fresh | `node` (str), `display_node` (str), `output` (dict with e.g. `images: [{filename, subfolder, type}]`), `prompt_id` (str) | `execution.py:562` (fresh), `execution.py:423` (cached) |
| `execution_error` | Any node raised an exception, **or** a node returned an `ExecutionBlocker` with a message | `prompt_id`, `node_id`, `node_type`, `executed` (list[str]), `exception_message`, `exception_type`, `traceback` (list[str]), `current_inputs`, `current_outputs` — see "Two emission sites" below for shape differences | `execution.py:684-695` (runtime error), `execution.py:511-525` (ExecutionBlocked) |
| `execution_interrupted` | User clicked interrupt (or `/interrupt` POSTed) mid-run — **broadcast** to all clients | `prompt_id`, `node_id`, `node_type`, `executed` (list[str]), `timestamp` (int ms) | `execution.py:682` |
| `execution_success` | Final success event for a prompt (fires before the terminating `executing: {node: null}`) | `prompt_id`, `timestamp` (int ms) | `execution.py:795` |

Every event except `status` also carries a `timestamp` (int, ms since epoch) when routed through `PromptExecutor.add_message` — it is injected unconditionally at `execution.py:661-664`. Direct `send_sync` calls (the `executing`, `executed`, and `progress` events) do **not** include a `timestamp`.

### Sample frames

`status` (on connect):

```json
{
  "type": "status",
  "data": {
    "status": {"exec_info": {"queue_remaining": 0}},
    "sid": "b1c9e7b0-2f9e-4a3a-9c2c-2c9e7b0b1c9e"
  }
}
```

`execution_start`:

```json
{
  "type": "execution_start",
  "data": {"prompt_id": "abcd1234", "timestamp": 1713459600123}
}
```

`execution_cached`:

```json
{
  "type": "execution_cached",
  "data": {"nodes": ["4", "5", "6", "7"], "prompt_id": "abcd1234", "timestamp": 1713459600125}
}
```

`executing` (node start, then terminator):

```json
{"type": "executing", "data": {"node": "3", "display_node": "3", "prompt_id": "abcd1234"}}
{"type": "executing", "data": {"node": null, "prompt_id": "abcd1234"}}
```

`progress` (per step):

```json
{"type": "progress", "data": {"value": 12, "max": 20, "prompt_id": "abcd1234", "node": "3"}}
```

`progress_state`:

```json
{
  "type": "progress_state",
  "data": {
    "prompt_id": "abcd1234",
    "nodes": {
      "3": {"value": 12, "max": 20, "state": "running", "node_id": "3",
            "prompt_id": "abcd1234", "display_node_id": "3",
            "parent_node_id": null, "real_node_id": "3"}
    }
  }
}
```

`executed`:

```json
{
  "type": "executed",
  "data": {
    "node": "9",
    "display_node": "9",
    "output": {
      "images": [
        {"filename": "ComfyUI_00001_.png", "subfolder": "", "type": "output"}
      ]
    },
    "prompt_id": "abcd1234"
  }
}
```

`execution_error`:

```json
{
  "type": "execution_error",
  "data": {
    "prompt_id": "abcd1234",
    "node_id": "3",
    "node_type": "KSampler",
    "executed": ["4", "5", "6", "7"],
    "exception_message": "CUDA out of memory...",
    "exception_type": "torch.cuda.OutOfMemoryError",
    "traceback": ["  File \"...\", line N, in ...\n", "..."],
    "current_inputs": {"seed": [5], "steps": [20]},
    "current_outputs": ["4", "5"],
    "timestamp": 1713459612847
  }
}
```

#### Two `execution_error` emission sites

`execution_error` events come from **two different code paths** that produce **different payload shapes**. CLI consumers must handle both.

- **Path 1 — runtime exception** (`execution.py:684-695`). Routed through `PromptExecutor.add_message`, which injects `timestamp` unconditionally (`execution.py:660-667`). `current_inputs` is a dict (e.g. `{"seed": [5], "steps": [20]}`), `current_outputs` is a list of node ids, `traceback` is a non-empty `list[str]`, `exception_type` is the real Python exception class name (e.g. `torch.cuda.OutOfMemoryError`).
- **Path 2 — ExecutionBlocked** (`execution.py:511-525`). A node returned an `ExecutionBlocker(message)`; the handler calls `server.send_sync("execution_error", mes, server.client_id)` **directly**, bypassing `add_message`. Consequences: **no `timestamp` field**, `current_inputs: []` (list, not dict), `current_outputs: []`, `traceback: []`, `exception_type` is the literal string `"ExecutionBlocked"`, and `exception_message` is prefixed `"Execution Blocked: "`.

Consumer implications: do not assume `timestamp` exists on an `execution_error`; do not assume `traceback` has entries; do not assume `current_inputs` is a dict. For `ExecutionBlocked` errors there is no usable stack trace — surface `exception_message` directly to the user.

`execution_success`:

```json
{"type": "execution_success", "data": {"prompt_id": "abcd1234", "timestamp": 1713459615001}}
```

## Binary frames

ComfyUI also sends **binary** WebSocket frames for latent preview images (and some other payloads). All binary frames share a 4-byte big-endian event-type header, packed via `struct.pack(">I", event)` in `server.py:1126-1133`. The rest of the frame is event-specific.

Binary event type codes live in `protocol.py`:

```python
class BinaryEventTypes:
    PREVIEW_IMAGE = 1               # header(4) + image_type(4) + image bytes
    UNENCODED_PREVIEW_IMAGE = 2     # internal: (image_type, PIL.Image, max_size) tuple; encoded server-side to PREVIEW_IMAGE
    TEXT = 3                        # header(4) + node_id_len(4) + node_id bytes + utf-8 text
    PREVIEW_IMAGE_WITH_METADATA = 4 # header(4) + metadata_len(4) + metadata JSON + image bytes
```

Note: `UNENCODED_PREVIEW_IMAGE` (type 2) is **never on the wire**. It is an internal enum; the dispatcher at `server.py:1114-1116` intercepts it in `send()` and re-routes to `send_image()`, which re-encodes the payload and transmits it as `PREVIEW_IMAGE` (type 1). Client readers will only ever observe types 1, 3, and 4.

### PREVIEW_IMAGE (event type 1)

Emitted by `send_image` (`server.py:1135-1157`) during sampling when a preview method is set. Layout:

| Bytes | Meaning |
| --- | --- |
| 0-3 | Event type (`>I`, value = 1) |
| 4-7 | Image format code (`>I`, 1 = JPEG, 2 = PNG) |
| 8-end | Encoded image bytes (JPEG or PNG) |

The ComfyUI example script decodes it as `Image.open(BytesIO(frame[8:]))` — the first 8 bytes are the stacked two `>I` headers (see `script_examples/websockets_api_example.py:42-45`).

### PREVIEW_IMAGE_WITH_METADATA (event type 4)

Only emitted when the client advertised `supports_preview_metadata` during feature-flag negotiation (`comfy_execution/progress.py:210-230`). Layout (`server.py:1188-1194`):

| Bytes | Meaning |
| --- | --- |
| 0-3 | Event type (`>I`, value = 4) |
| 4-7 | Metadata JSON length (`>I`) |
| 8-(8+len) | UTF-8 JSON metadata (`{node_id, prompt_id, display_node_id, parent_node_id, real_node_id, image_type}`) |
| rest | Raw PNG or JPEG image bytes (format indicated by `metadata.image_type`) |

### TEXT (event type 3)

Emitted by `send_progress_text` (`server.py:1278-1288`). Layout: `event(4) + node_id_len(4) + node_id bytes + utf-8 text`.

### SaveImageWebsocket node

The built-in `SaveImageWebsocket` node sends finished images as `PREVIEW_IMAGE` binary frames instead of writing to disk — `script_examples/websockets_api_example_ws_images.py:45-48` shows the idiomatic `out[8:]` extraction pattern for consumers.

## Complete client pattern

A robust Python client needs to:

1. Open the WebSocket **before** submitting the prompt.
2. Use a `client_id` that matches on both sides (unique per client — see Gotchas #6 and #7).
3. Treat **any** of these as a terminator (match by `prompt_id` where present): `executing` with `node: null` (the primary signal, always fires — `script_examples/websockets_api_example.py:39-40`, `main.py:325`); `execution_success` (clean-completion, `execution.py:795`); `execution_error`; `execution_interrupted`. Listen for all four — `execution_success` in particular was previously documented but not handled in the loop.
4. Set a read timeout on the WebSocket (`ws.settimeout(...)`) so a wedged executor cannot block the CLI forever; broken connections are silently dropped server-side (Gotcha #8).
5. If you **reconnect** mid-run, the replay `executing` event from `server.py:276-277` arrives **without** a `prompt_id` — a strict `prompt_id` filter will drop it. Pull `/history/{prompt_id}` on startup to check whether the prompt already finished, then fall back to waiting for the next sampler step.
6. Pull `/history/{prompt_id}` at the end to resolve final output file paths.

```python
import json, struct, uuid, urllib.request, urllib.parse
import websocket  # pip install websocket-client

def run_workflow(server: str, workflow: dict, preview_dir: str | None = None) -> dict:
    client_id = str(uuid.uuid4())
    ws = websocket.WebSocket()
    ws.connect(f"ws://{server}/ws?clientId={client_id}")
    # Detect a wedged executor — without a timeout, a dropped connection leaves
    # you blocked in ws.recv() forever (see Gotcha "send_socket_catch_exception").
    ws.settimeout(120)

    # Submit prompt (client_id MUST match).
    body = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
    req = urllib.request.Request(
        f"http://{server}/prompt", data=body,
        headers={"Content-Type": "application/json"},
    )
    prompt_id = json.loads(urllib.request.urlopen(req).read())["prompt_id"]

    # If you reconnect mid-run, the server replays the last `executing` event WITHOUT
    # a `prompt_id` (server.py:276-277) — a strict prompt_id filter will silently drop
    # it. Best practice on reconnect: first GET /history/<prompt_id> to check whether
    # the prompt has already finished; otherwise fall through to the event loop and
    # wait for the next sampler step / `executed` event to re-confirm the active node.

    done = False
    error = None
    preview_idx = 0
    try:
        while not done:
            frame = ws.recv()
            if isinstance(frame, (bytes, bytearray)):
                # Binary preview: first 4 bytes = event type, next 4 = image format,
                # rest = JPEG/PNG bytes (see "PREVIEW_IMAGE" section).
                (event_type,) = struct.unpack(">I", frame[:4])
                if event_type == 1 and preview_dir is not None:  # PREVIEW_IMAGE
                    with open(f"{preview_dir}/preview_{preview_idx:04d}.jpg", "wb") as f:
                        f.write(frame[8:])
                    preview_idx += 1
                continue
            msg = json.loads(frame)
            etype, data = msg["type"], msg["data"]
            if etype == "progress" and data.get("prompt_id") == prompt_id:
                # Update Rich progress bar for data["node"] with value/max.
                pass
            elif etype == "executing" and data.get("prompt_id") == prompt_id:
                if data["node"] is None:
                    done = True  # Primary terminator — always fires (main.py:325).
            elif etype == "execution_success" and data.get("prompt_id") == prompt_id:
                done = True  # Clean-completion terminator (fires before the `executing: null`).
            elif etype == "execution_error" and data.get("prompt_id") == prompt_id:
                error = data
                done = True
            elif etype == "execution_interrupted" and data.get("prompt_id") == prompt_id:
                error = {"exception_message": "Interrupted", **data}
                done = True
    finally:
        ws.close()

    if error:
        raise RuntimeError(f"[{error['exception_type']}] {error['exception_message']}")

    # Resolve final file paths via /history — the ws 'executed' event only gives
    # filename/subfolder/type, not absolute paths, and does not fire for non-UI nodes.
    with urllib.request.urlopen(f"http://{server}/history/{prompt_id}") as r:
        history = json.loads(r.read())[prompt_id]
    return history  # history["outputs"][node_id]["images"] -> [{filename, subfolder, type}]
```

## CLI integration

The cli-me skill exposes two live-progress entry points backed by this protocol:

- `comfyui queue wait <prompt_id> --live` — attaches to the running prompt's stream and renders a Rich progress panel.
- `comfyui workflow run <file.json> [--live / --no-live]` — submits the workflow and (default `--live`) streams progress until completion.

The rendering loop uses a Rich `Progress` with one task per active node:

```python
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

def render(events):
    with Progress(
        TextColumn("[bold]{task.fields[node_label]}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        transient=False,
    ) as prog:
        tasks: dict[str, int] = {}
        for msg in events:
            etype, data = msg["type"], msg["data"]
            if etype == "executing" and data.get("node"):
                node = data["node"]
                label = f"Node {data.get('display_node', node)}"
                if node not in tasks:
                    tasks[node] = prog.add_task("", total=1, node_label=label)
            elif etype == "progress":
                node = data["node"]
                if node not in tasks:
                    tasks[node] = prog.add_task(
                        "", total=data["max"], node_label=f"Node {node}"
                    )
                prog.update(tasks[node], total=data["max"], completed=data["value"])
            elif etype == "executed":
                node = data["node"]
                if node in tasks:
                    prog.update(tasks[node], completed=prog.tasks[tasks[node]].total)
```

Key design notes:

- Start one Rich task per `executing` node, not per prompt — ComfyUI sends `progress` events for **multiple** nodes in a single run (the KSampler loop is the loud one; VAE decode is silent).
- For the KSampler specifically, `progress.max` is the configured `steps`; use it as the task total.
- Close each task on `executed` (UI nodes) or on the next `executing` (non-UI nodes), whichever comes first.
- For `--live` on `queue wait`, always also watch the `status` event so the CLI can show "N ahead in queue" before your prompt starts.

## Gotchas

1. **`client_id` routing is more nuanced than "matches or silence" — and prompts submitted without one broadcast everything.** Targeted events (`executing`, `progress`, `executed`, `execution_error`, `execution_success`, `execution_start`, `execution_cached`, `progress_state`) are routed by `sid == server.client_id` — the executor sets `server.client_id = extra_data["client_id"]` at `execution.py:719` for prompts that include a `client_id`. Two regimes to understand:
   - **Prompt submitted WITH `client_id`.** Only `execution_interrupted` (`execution.py:682`, `broadcast=True`) and `status` (`server.py:1221`) reach all clients; every other event targets only that client's socket. If your WebSocket's `clientId` does not match, you see nothing but broadcasts.
   - **Prompt submitted WITHOUT `client_id`.** The executor falls through the `else` at `execution.py:720-721` and sets `server.client_id = None`. Every `send_sync(..., None)` call then has no matching `sid` in `self.sockets`, and `send_json` / `send_bytes` fall back to broadcasting to **every** connected socket. In this mode your client receives events for prompts it did not submit — and so does every other connected client.
   Always pass `client_id` in `POST /prompt` (and match it on the WebSocket URL) if you care about isolation between concurrent CLIs/tabs.

2. **Binary frames need a different decode path than JSON.** A `ws.recv()` call can return either `str` (JSON message) or `bytes` (binary frame). Dispatch on `isinstance(frame, (bytes, bytearray))`. Do not `json.loads` every frame, and do not `len(frame) < 8` without handling the TEXT and PREVIEW_IMAGE_WITH_METADATA variants. The canonical pattern is `out[8:]` for plain `PREVIEW_IMAGE` (skip 4-byte event type + 4-byte format code); use the length-prefixed metadata header for `PREVIEW_IMAGE_WITH_METADATA`.

3. **`executed.output.images` gives filename+subfolder+type, not paths.** You still have to call `GET /history/{prompt_id}` (or `GET /view?filename=...&subfolder=...&type=...`) to turn those triples into bytes on disk. The WebSocket `executed` event is great for "this node produced N images" UI hints but is not a substitute for the history pull — and it only fires for **UI output nodes** (`len(output_ui) > 0` check at `execution.py:551`), so a workflow with only a `SaveImage` node will emit `executed`, but one that only writes a file via a custom node without `UI` metadata will not.

4. **`execution_success` is not guaranteed on failure paths.** Use `executing` with `node: null` AND `prompt_id` match as your primary "done" signal (as the ComfyUI example itself does). `execution_success` fires only on clean completion (`execution.py:795`, inside the `else` of the `while` loop); on error the executor `break`s out and the success event is skipped — but the terminator `{"executing": {"node": null}}` **always** fires from `main.py:325` at the end of `prompt_worker`.

5. **`progress_state` and `progress` overlap.** Both events are emitted for every sampler step (see `main.py:389` triggering the registry, which in turn emits `progress_state` via `WebUIProgressHandler.update_handler`). Subscribe to one or the other, not both, to avoid double-counting. `progress` is simpler (one node per message); `progress_state` is a full snapshot of all active nodes — better for multi-node dashboards. Note: `progress_state.nodes` contains only running/finished nodes, not pending — the dict comprehension at `comfy_execution/progress.py:179-181` filters out `NodeState.Pending`, so you cannot use it to enumerate the full graph.

6. **Duplicate `clientId` silently evicts the earlier socket.** `server.py:261-263` calls `self.sockets.pop(sid, None)` whenever a new connection arrives with a `clientId` that is already registered. The old WebSocket receives no close frame — it just stops receiving events (and stops appearing in the routing dict). Use a unique UUID per client; never share a hard-coded `clientId` across CLI invocations.

7. **Empty-string `clientId=` generates a fresh id server-side.** `server.py:260` reads `clientId` with default `''`, and `server.py:264-265` treats a falsy value as "no id — generate one" (`uuid.uuid4().hex`). If you connect with `?clientId=` and no value, the server picks a new id and sends it back in the first `status.sid`, but you never told your prompt submitter what that id is. Always generate the UUID client-side and pass it in both places.

8. **`send_socket_catch_exception` silently drops broken clients.** `server.py:62-66` wraps every outgoing frame and swallows `ClientError`, `ClientPayloadError`, `ConnectionResetError`, `BrokenPipeError`, `ConnectionError` with a `logging.warning`. Your client will not receive a close frame when the server decides it is gone — if your network flaps, you may keep `ws.recv()`-ing forever. Combine with a heartbeat / `ws.settimeout(...)` to detect wedged connections.

## Sources

External:

- ComfyUI WebSocket example (official): https://github.com/comfyanonymous/ComfyUI/blob/master/script_examples/websockets_api_example.py
- ComfyUI WebSocket + SaveImageWebsocket example: https://github.com/comfyanonymous/ComfyUI/blob/master/script_examples/websockets_api_example_ws_images.py
- `websocket-client` Python library: https://github.com/websocket-client/websocket-client
- ComfyUI API docs portal: https://docs.comfy.org/ (see "Essentials / API" for current coverage)

In-tree source references (paths under `E:\workspaces\tools\comfy\ComfyUI\`):

- `server.py:62-66` — `send_socket_catch_exception` swallows network errors (silent client drops).
- `server.py:256-314` — `@routes.get('/ws')` handler; `server.py:260` reads `clientId` query param; `server.py:261-263` evicts any existing socket registered under the same `sid`; `server.py:264-265` generates a fresh uuid when `clientId` is empty; `server.py:274` sends initial `status` with `sid`; `server.py:276-277` reconnect-resume `executing` replay (no `prompt_id`); `server.py:295-299` feature-flags handshake reply.
- `server.py:1107-1112` — `get_queue_info()` — shape of `status.exec_info`.
- `server.py:1114-1124` — `send()` dispatch between JSON and binary paths.
- `server.py:1126-1133` — `encode_bytes()` — binary header format (`>I` event type prefix).
- `server.py:1135-1157` — `send_image()` — PREVIEW_IMAGE frame layout.
- `server.py:1159-1194` — `send_image_with_metadata()` — PREVIEW_IMAGE_WITH_METADATA layout.
- `server.py:1196-1214` — `send_bytes`, `send_json` — routing by `sid`.
- `server.py:1216-1221` — `send_sync` queue push, `queue_updated` broadcast.
- `server.py:1278-1288` — `send_progress_text` — TEXT binary frame layout.
- `protocol.py:1-7` — `BinaryEventTypes` enum.
- `execution.py:419-425` — `_send_cached_ui` — cached `executed` emission.
- `execution.py:481-485` — `executing` emission at node start.
- `execution.py:511-526` — `execution_error` emission for `ExecutionBlocked` (direct `send_sync`, bypasses `add_message`; no `timestamp`, empty `current_inputs`/`current_outputs`/`traceback`).
- `execution.py:684-695` — `execution_error` emission for runtime exceptions (routed via `add_message`; includes `timestamp`).
- `execution.py:720-721` — `server.client_id = None` when prompt submitted without `client_id` (causes every targeted event to broadcast).
- `execution.py:551-562` — `executed` emission for fresh UI outputs.
- `execution.py:660-667` — `PromptExecutor.add_message` — unconditional `timestamp` injection.
- `execution.py:676-695` — `execution_interrupted` / `execution_error` message shape.
- `execution.py:713-724` — `execute_async` sets `server.client_id` and fires `execution_start`.
- `execution.py:751-753` — `execution_cached` payload.
- `execution.py:795` — `execution_success` emission.
- `main.py:324-325` — terminal `executing: {node: null}` emission at end of `prompt_worker`.
- `main.py:376-405` — `hijack_progress` — `progress` event + `UNENCODED_PREVIEW_IMAGE` fallback.
- `comfy_execution/progress.py:150-230` — `WebUIProgressHandler` — `progress_state` event + `PREVIEW_IMAGE_WITH_METADATA` feature-gated path; `comfy_execution/progress.py:179-181` filters out `NodeState.Pending` so `progress_state.nodes` is running/finished only.
- `script_examples/websockets_api_example.py:29-57` — canonical stop-on-`executing(null)` loop.
- `script_examples/websockets_api_example_ws_images.py:29-50` — `out[8:]` binary decode pattern.
