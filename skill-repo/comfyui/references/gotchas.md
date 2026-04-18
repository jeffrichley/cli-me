# ComfyUI Gotchas

Footguns discovered during source analysis and adversarial review. Each
entry cites the technique page with the full detail.

## HTTP / API

### Origin-guard 403 on mismatched Origin/Host
When ComfyUI is bound to a non-loopback interface, it rejects requests whose
`Origin` header doesn't match the server's bind host. Symptom: `403 Forbidden`
with no JSON body. Fix: set `Origin: <base_url>` on every HTTP request — the
CLI does this automatically in `backend.http_client()`.

See [techniques/server-info-and-errors.md](techniques/server-info-and-errors.md).

### `/prompt` returns 400 (not 422) on validation failure
Workflow validation failures (missing nodes, bad inputs, unknown class_type)
come back as HTTP 400 with a body like `{"error": {...}, "node_errors": {...}}`.
Don't expect 422 "Unprocessable Entity" — most REST conventions use 422 here.

See [techniques/queue-api.md](techniques/queue-api.md).

### No `--max-queue-size` flag exists
The queue is unbounded. There's no server-side backpressure. A misbehaving
client can enqueue thousands of prompts. Always guard your own submissions.

See [techniques/queue-api.md](techniques/queue-api.md).

### Duplicate `prompt_id` silently overwrites history
Submitting the same `prompt_id` twice (for clients that supply their own)
will silently replace the older `/history` entry. The server returns success
either way. Never reuse a prompt_id.

See [techniques/queue-api.md](techniques/queue-api.md).

## WebSocket

### Clients without `client_id` become the broadcast sink
If a WebSocket client connects without `?clientId=...`, the server sets its
internal `server.client_id` to `None` and subsequent events are broadcast
to *every* connected client. Always pass a stable `client_id`.

See [techniques/websocket-progress.md](techniques/websocket-progress.md).

### Two terminators for prompt completion
A prompt can finish with EITHER an `execution_success` event OR an
`executing` event whose `node` field is `null`. Depending on version and
execution path, only one may appear. `ws_client.watch()` must treat both
as terminators.

See [techniques/websocket-progress.md](techniques/websocket-progress.md).

### `execution_error` has two emission paths
`execution_error` is emitted both from node-level exceptions and from
`ExecutionBlocked` signals. The `ExecutionBlocked` variant carries an
empty traceback — don't assume traceback is always populated.

See [techniques/websocket-progress.md](techniques/websocket-progress.md).

## Workflow formats

### PNG `prompt` chunk = API format, `workflow` chunk = UI format
ComfyUI writes two tEXt/iTXt chunks into every PNG it saves. Don't confuse
them: `prompt` is the flat API-format dict, `workflow` is the node-graph UI
format. Extract the one the caller asks for.

See [techniques/workflow-formats.md](techniques/workflow-formats.md).

### WebP `workflow:` tag position is not guaranteed at 0x010F
For WebP outputs, the embedded workflow lives in an EXIF user-comment tag
whose offset varies. Scanning descending from the file end (not a hardcoded
offset) is the reliable approach.

See [techniques/workflow-formats.md](techniques/workflow-formats.md).

## Models and inputs

### No listing endpoint for /input
`GET /input` does not exist. The CLI's `input list` command therefore
requires `--local` and reads the filesystem directly — don't expect a
remote listing to ever work.

See [techniques/input-output.md](techniques/input-output.md).

### `checkpoints/` vs `diffusion_models/` — loader mismatch
Single-file bundled checkpoints (SDXL, Flux-fp8 all-in-one) load via
`CheckpointLoaderSimple` from `checkpoints/`. Standalone UNETs (split
Flux, SD3, WAN, HunyuanVideo, Kontext) load via `UNETLoader` from
`diffusion_models/`. Dropping a file in the wrong folder makes the
loader say "value not in list" even though the file exists on disk.

See [techniques/model-acquisition.md](techniques/model-acquisition.md).

### PyPI `nunchaku` is NOT the SVDQuant library
`pip install nunchaku` from PyPI installs a Gibbs sampler for Bayesian
models — unrelated to the ComfyUI-nunchaku custom node. The real
SVDQuant inference library lives only at
`github.com/nunchaku-tech/nunchaku/releases` as pre-built wheels keyed
to specific CUDA + torch + Python + OS combos. General lesson:
"ImportError: cannot import name X from Y" often means the wrong
package is installed under the expected name, not that the right one
is missing.

See [techniques/model-acquisition.md](techniques/model-acquisition.md).

### `/object_info` cache is mtime-based — restart if your FS doesn't bump dir mtime
ComfyUI auto-refreshes its model lists when a folder's mtime changes
(new download, deleted file). On some Windows/network-FS configs the
mtime doesn't bump, and `model list` keeps returning stale data. If
that happens, restart ComfyUI — there's no in-core refresh endpoint.

See [techniques/model-acquisition.md](techniques/model-acquisition.md).

### UI-format workflows can't auto-convert to API format in v1
ComfyUI's `graphToPrompt()` conversion lives in the web frontend, not
the server. A UI-format `.json` (`{"nodes": [...], "links": [...]}`)
cannot be submitted to `/prompt` and this skill cannot convert it.
Either extract an API-format PNG that the same workflow produced,
load the UI-format into the web editor and re-export via Dev mode,
or hand-roll the API form. v2 could add a headless converter that
round-trips through a running ComfyUI — not present in v1.

See [techniques/flow-acquisition.md](techniques/flow-acquisition.md).
