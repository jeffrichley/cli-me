---
title: ComfyUI Server Info and Error Handling
description: /system_stats, /embeddings, health checks, and how the CLI surfaces validation and runtime errors.
---

# ComfyUI Server Info and Error Handling

ComfyUI exposes a handful of introspection endpoints and a small but opinionated
error surface. The CLI wraps both so users get fast health checks and legible,
actionable error messages instead of raw HTTP dumps.

## GET /system_stats

This is the single most useful endpoint for a CLI. It is cheap, returns 200
when the server is alive, and exposes enough information to verify CUDA is
working and the right ComfyUI version is running.

**Exact response shape** (grounded in `server.py:646-685`):

```json
{
  "system": {
    "os": "win32",
    "ram_total": 68517556224,
    "ram_free": 34812923904,
    "comfyui_version": "0.3.30",
    "required_frontend_version": "1.16.9",
    "installed_templates_version": "0.1.22",
    "required_templates_version": "0.1.22",
    "python_version": "3.12.7 (tags/v3.12.7:0b05ead, Oct  1 2024, 03:06:41) [MSC v.1941 64 bit (AMD64)]",
    "pytorch_version": "2.5.1+cu124",
    "embedded_python": false,
    "argv": ["main.py", "--listen", "127.0.0.1", "--port", "8188"]
  },
  "devices": [
    {
      "name": "cpu",
      "type": "cpu",
      "index": null,
      "vram_total": 68517556224,
      "vram_free": 34812923904,
      "torch_vram_total": 0,
      "torch_vram_free": 0
    }
  ]
}
```

Note: `index` is `null` for CPU devices (ComfyUI launched with `--cpu`); for
CUDA devices it is the integer device index (e.g., `0`). On GPU hosts the
`name` looks like `"cuda:0 NVIDIA GeForce RTX 4090 : cudaMallocAsync"` and
`type` is `"cuda"`.

Memory values are raw bytes from `comfy.model_management.get_total_memory` /
`get_free_memory` (`comfy/model_management.py:209`, `:1483`). The CLI should
format to GiB for human output and keep bytes in `--json` mode.

## GET /embeddings

Returns a JSON array of embedding names (no extension). Grounded in
`server.py:324-327`:

```json
["easynegative", "badhandv4", "ng_deepnegative_v1_75t"]
```

Useful for autocomplete in the CLI, and for validating that a workflow's
embedding references resolve on the target server.

## GET /extensions

Returns a list of frontend extension JS URLs (`server.py:343-355`). Not
interesting to CLI users directly but useful for debugging "why doesn't my
custom node show a widget in the UI" style questions.

## Health check patterns

ComfyUI has **no dedicated `/health` or `/ready` endpoint**. The CLI uses:

- `GET /system_stats` — fast (~10 ms on a warm server), 200 on a live server,
  and the response proves the Python event loop, torch, and the model manager
  all imported successfully. This is the ping of choice.
- `GET /` — returns the web UI HTML. A 200 here only proves aiohttp is up; it
  does not prove ComfyUI itself is ready (see cold-start gotcha below). Do not
  rely on this for readiness.

The CLI's `comfyui ping` command uses `/system_stats`.

## Error taxonomy

The CLI must distinguish and surface these six categories. Each maps to a
distinct exit code so shell scripts and CI can branch on them.

### 1. Connection refused / DNS failure — exit 2

The server is not running, wrong host, or firewalled. `httpx` raises
`httpx.ConnectError` / `httpx.ConnectTimeout`.

```
comfyui: ComfyUI is not running at http://127.0.0.1:8188.
         Start it with: python main.py
         (in E:\workspaces\tools\comfy\ComfyUI)
```

### 2. HTTP 400 from /prompt with node_errors — exit 3

Workflow validation failed. Response body shape (grounded in
`server.py:960` and `execution.py:1155-1184`):

```json
{
  "error": {
    "type": "prompt_outputs_failed_validation",
    "message": "Prompt outputs failed validation",
    "details": "Required input is missing: ckpt_name: \nValue not in list: ckpt_name: 'sd_xl_base_1.0.safetensors' not in ['v1-5-pruned.ckpt']\nRequired input is missing: text: ",
    "extra_info": {}
  },
  "node_errors": {
    "4": {
      "errors": [
        {
          "type": "value_not_in_list",
          "message": "Value not in list",
          "details": "ckpt_name: 'sd_xl_base_1.0.safetensors' not in ['v1-5-pruned.ckpt']",
          "extra_info": {
            "input_name": "ckpt_name",
            "input_config": null,
            "received_value": "sd_xl_base_1.0.safetensors"
          }
        }
      ],
      "dependent_outputs": ["9"],
      "class_type": "CheckpointLoaderSimple"
    }
  }
}
```

Pretty-print as:

```
Workflow validation failed (3 errors in 2 nodes):

  node #4 CheckpointLoaderSimple
    - value_not_in_list: ckpt_name 'sd_xl_base_1.0.safetensors' not in
      ['v1-5-pruned.ckpt']
    (blocks output: #9)

  node #6 CLIPTextEncode
    - required_input_missing: text
```

Note: `error.details` is a newline-joined string of
`"{message}: {details}"` entries — one line per individual error across all
bad outputs (grounded in `execution.py:1169-1173`). The per-node breakdown
lives under `node_errors`; use that for structured output and reserve
`error.details` for a flat summary.

Other `error.type` values seen in source (`execution.py:1065-1184`):
`missing_node_type` (custom node not installed), `prompt_no_outputs`,
`exception_during_validation`, `no_prompt`.

### 3. execution_error over websocket — exit 4

Runtime failure mid-execution. Comes as a WS message, not an HTTP response.
There are **two distinct emission paths** for `execution_error` and the CLI
must render both:

- **Runtime error** (`execution.py:684-695`, via `handle_execution_error` →
  `add_message`). Full payload: populated `traceback` (multi-line strings),
  real `current_inputs` / `current_outputs`, a `timestamp` attached by
  `add_message`, and an `exception_type` like `torch.cuda.OutOfMemoryError`.
- **ExecutionBlocked** (`execution.py:511-525`, `execution_block_cb`).
  Emitted via `server.send_sync` directly — **bypasses `add_message`**, so:
  - no `timestamp` field,
  - `traceback: []`,
  - `current_inputs: []`, `current_outputs: []`,
  - `exception_type: "ExecutionBlocked"`,
  - `exception_message` is `"Execution Blocked: {block.message}"`.

CLI rendering must not assume a non-empty `traceback` or a `timestamp` — an
ExecutionBlocked event is a legitimate failure that shows nothing in those
fields. Treat `exception_type == "ExecutionBlocked"` as a distinct sub-case
and render the block message verbatim.

Runtime-error payload (`execution.py:684-695`):

```json
{
  "type": "execution_error",
  "data": {
    "prompt_id": "abc-123",
    "node_id": "11",
    "node_type": "KSampler",
    "executed": ["4", "6", "7"],
    "exception_message": "CUDA out of memory. Tried to allocate 2.00 GiB...",
    "exception_type": "torch.cuda.OutOfMemoryError",
    "traceback": ["  File \"...\", line 123, in sample\n    ...\n"],
    "current_inputs": [],
    "current_outputs": []
  }
}
```

Surface as:

```
Execution failed at node #11 (KSampler):
  torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.00 GiB
  Executed before failure: 4, 6, 7
  Run `comfyui last-error --traceback` for the full stack trace.
```

Common causes: OOM, model file missing at load time, corrupt safetensors,
sampler shape mismatch.

### 4. HTTP 404 from /view — exit 5

Requested output doesn't exist: wrong `filename`, wrong `subfolder`, wrong
`type` (`output` / `input` / `temp`), or the file was cleaned up.

```
comfyui: output not found: subfolder='characters' filename='hero_00042_.png'
         Check `comfyui history <prompt_id>` for the actual filenames.
```

### 5. HTTP 403 from any endpoint (Origin mismatch) — exit 2

ComfyUI ships an **origin-only middleware that is on by default**
(`server.py:219-232`, `create_origin_only_middleware` at `server.py:~140-184`).
When the server is launched *without* `--enable-cors-header`, the else branch
installs `create_origin_only_middleware()`, which rejects any request where
the `Origin` header doesn't match the `Host` header with a bare
`web.Response(status=403)` (`server.py:174-175`).

Symptoms: requests work from the ComfyUI web UI but fail from a CLI when:

- the server is hit via a different hostname than it binds to (e.g.,
  launched with `--listen 0.0.0.0` but hit as `http://192.168.1.10:8188`
  while the client sends `Origin: http://127.0.0.1:8188`),
- a reverse proxy rewrites `Host` but the client's `Origin` still points
  at the internal URL,
- a CLI sets `Origin` manually and it doesn't match the target `Host`.

Fix (in order of preference):

1. Have the HTTP client send `Origin` matching the server's base URL (same
   scheme + host + port the CLI is connecting to), or omit `Origin`
   entirely — the middleware only enforces a match when `Origin` is
   present and the host is loopback.
2. Launch ComfyUI with `--enable-cors-header '*'` (or a specific origin),
   which swaps the origin-only middleware out for a permissive CORS
   middleware.

### 6. HTTP non-2xx (other than 400/404/403) — exit 1

Catch-all for anything the taxonomy above doesn't cover: 500 from a handler
bug, 405 from the wrong verb, 413 from `--max-upload-size`, 401/403 from a
reverse proxy fronting ComfyUI, etc. ComfyUI itself does **not** enforce a
queue-size limit — there is no `--max-queue-size` flag
(`comfy/cli_args.py`) and `PromptQueue` is unbounded — so a 503 from
`/prompt` means an upstream proxy or load balancer, not ComfyUI. Surface
the response body verbatim as context and exit 1.

### Timeouts

`httpx`'s default is 5 s, which is wrong for every interesting operation.
The CLI sets:

| Operation            | Timeout        |
| -------------------- | -------------- |
| `/system_stats`, `/embeddings`, `/queue`, `/history` | 10 s |
| `POST /prompt` (validation + enqueue) | 30 s |
| `queue wait` / websocket consumption  | no timeout |
| `/view` download     | 120 s (large images / videos) |

Always surface timeout separately from connection refused — "server is slow"
and "server is down" need different fixes.

## CLI error UX

One-line human-readable summary on stderr, Rich-formatted with red for the
error tag, and a distinct exit code per category:

| Exit | Meaning                                    |
| ---- | ------------------------------------------ |
| 0    | success                                    |
| 1    | generic / unexpected server error (non-2xx not otherwise classified; body surfaced as context) |
| 2    | server unreachable or forbidden (connection refused / DNS / timeout on ping / 403 Origin mismatch) |
| 3    | workflow validation (400 with node_errors) |
| 4    | execution error (ws `execution_error`, both runtime and ExecutionBlocked variants) |
| 5    | resource not found (/view 404, history miss) |

Machine-readable details go to `--json` output; the pretty stderr line is
always present so humans scrolling logs see the cause immediately.

## CLI Commands

### `comfyui ping`

`GET /system_stats`, print a one-line `ok (...)` summary on success. Exit 0 on
200, exit 2 on connection/origin failures, exit 1 on other non-2xx responses,
per the taxonomy table above. Honors the URL precedence below.

```
$ comfyui ping
ok (ComfyUI 0.19.0 — cuda NVIDIA GeForce RTX 4090)
```

### `comfyui info`

Pretty-print `/system_stats` as a table:

```
System
  OS               win32
  ComfyUI          0.3.30
  Python           3.12.7
  PyTorch          2.5.1+cu124
  RAM              32.4 / 63.8 GiB free
  Embedded Python  no
  Launch args      main.py --listen 127.0.0.1 --port 8188

Devices
  [0] cuda  NVIDIA GeForce RTX 4090
      VRAM       22.6 / 24.0 GiB free
      torch VRAM  0.0 /  0.0 GiB free
```

### `comfyui info --json`

Raw `/system_stats` response, unmodified. Intended for `jq` pipelines and CI
assertions.

## Gotchas

1. **/system_stats is not instantaneous on cold start.** On first launch
   ComfyUI imports torch, scans `custom_nodes/`, and initializes the model
   manager before the HTTP server accepts connections. Typical cold-start time
   is **~5–20 s** on an SSD, much longer with many custom nodes or on a cold
   Windows filesystem. `comfyui ping` during that window returns connection
   refused, not a slow 200 — bump `--timeout` or retry in a shell loop.

2. **ComfyUI has no authentication by default.** There is no token, API key,
   or basic-auth middleware in `server.py`. Launching with `--listen 0.0.0.0`
   (or any non-loopback address) exposes the full API — including `/prompt`,
   `/view`, and file uploads — to the network. Use an SSH tunnel or reverse
   proxy with auth for remote access.

3. **Never bake in `127.0.0.1:8188`.** Resolve the URL with this precedence,
   highest first:

   1. `--url` flag on the command
   2. `COMFY_URL` environment variable
   3. `url` key in the CLI's config file (`~/.config/cli-me/comfyui.toml`)
   4. Default `http://127.0.0.1:8188`

   This lets users point the same command at a dev box, a LAN GPU server, or
   an SSH-tunneled remote without editing scripts.

   Both `http://` and `https://` schemes are accepted in `--url` and
   `COMFY_URL`. ComfyUI itself doesn't terminate TLS — a reverse proxy
   (nginx, Caddy, Traefik) does. Behind a TLS proxy, the client's `Origin`
   header must match the **external** URL the CLI is talking to, not the
   internal `http://127.0.0.1:8188` ComfyUI is bound to — otherwise the
   origin-only middleware returns 403 (see error taxonomy #5 above).

4. **Middleware stack is opinionated by default.** ComfyUI installs, in order,
   `[cache_control, deprecation_warning, origin_only_middleware]` when
   `--enable-cors-header` is not set (`server.py:219-232`). The third
   middleware is the Origin-guard described in error taxonomy #5 and is the
   single most common source of "works in the UI, fails from my CLI" reports.
   Optional middlewares appended after that, conditionally: `compress_body`
   (`--enable-compress-response-body`), `block_external_middleware`
   (`--disable-api-nodes`), and the ComfyUI-Manager middleware
   (`--enable-manager`).

## Sources

- `server.py:646-685` — `/system_stats` route and response shape
- `server.py:324-327` — `/embeddings` route
- `server.py:343-355` — `/extensions` route
- `server.py:501` — `/view` route (404 on missing file)
- `server.py:915-968` — `POST /prompt`, validation failure shape, 400 envelope
- `server.py:140-184` — `create_origin_only_middleware` (403 on Origin/Host mismatch)
- `server.py:219-232` — default middleware stack assembly
- `execution.py:1065-1184` — `validate_prompt`, `node_errors` structure, `error.details` assembly (`:1169-1173`)
- `execution.py:684-695` — `handle_execution_error`, runtime `execution_error` payload
- `execution.py:511-525` — `execution_block_cb`, `ExecutionBlocked` `execution_error` payload
- `comfy/cli_args.py` — confirmed: no `--max-queue-size` flag exists; queue is unbounded
- `comfy/model_management.py:209,1483` — `get_total_memory`, `get_free_memory`
- ComfyUI docs: https://docs.comfy.org/development/comfyui-server/comms_routes
- ComfyUI docs: https://docs.comfy.org/development/comfyui-server/comms_messages
