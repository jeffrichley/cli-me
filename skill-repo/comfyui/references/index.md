# ComfyUI Wiki

## Source analysis

- [Analyzed version](source-analysis/analyzed-version.md) — ComfyUI version, commit, clone date
- [API surface](source-analysis/api-surface.md) — HTTP routes, request/response shapes
- [CLI interface](source-analysis/cli-interface.md) — ComfyUI's own `main.py` flags and startup
- [Key functions](source-analysis/key-functions.md) — important functions with file paths and line numbers
- [WebSocket events](source-analysis/websocket-events.md) — full /ws event catalog

## Techniques

- [Queue API](techniques/queue-api.md) — /prompt, /queue, /history, /interrupt, /free
- [WebSocket progress](techniques/websocket-progress.md) — /ws events, terminators, client_id routing
- [Workflow formats](techniques/workflow-formats.md) — UI vs API format, conversion, embedding
- [Workflow params](techniques/workflow-params.md) — parameter substitution syntax and tricks
- [Models and assets](techniques/models-and-assets.md) — model types, /models endpoint, folder layout
- [Input / output](techniques/input-output.md) — /upload/image, /view, /history output shape
- [Server info and errors](techniques/server-info-and-errors.md) — /system_stats, origin-guard, HTTP error codes

## Operational

- [Gotchas](gotchas.md) — known issues, footguns, and workarounds
- [Log](log.md) — chronological record of research and changes
