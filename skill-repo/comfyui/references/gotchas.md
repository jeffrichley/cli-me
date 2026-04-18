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
