# ComfyUI Skill Build Log

## 2026-04-18: Initial research completed

Analyzed ComfyUI v0.19.0 (commit acd7185). Created source analysis (5 pages) and
7 technique pages covering queue API, websocket progress, workflow formats,
parameter substitution, model discovery, input/output, and error handling.
Phase 1d R1 adversarial review completed with 63 findings across 7 pages
(5 Critical, 24 Major, 34 Minor) — all fixed.

## 2026-04-18: Phase 2 scaffold

Scaffolded `comfyui-cli` package with 19 commands across 6 groups
(`server`, `queue`, `workflow`, `model`, `input`, `output`). All command
implementations are stubs that raise `NotImplementedError` — real logic
arrives in Phase 3. Backend module (`backend.py`) defines URL resolution,
httpx client factory with `Origin` header set, and the typed `ComfyError`
exception hierarchy (`ComfyConnectionError`, `ComfyValidationError`,
`ComfyExecutionError`, `ComfyNotFoundError`, `ComfyOriginError`) with
distinct exit codes. WebSocket client (`ws_client.py`) is a skeleton only.

## 2026-04-18: Phase 3 QA-first implementation complete

All 19 commands implemented against live ComfyUI v0.19.0. Adversarial
reviews (R3 code-wiki alignment + R4 test quality) for each group surfaced
2 Critical, 11 Major, and 22 Minor findings; all Critical + Major fixed.

**Critical fixes shipped:**
- `workflow extract` WebP decoder now scans EXIF tags descending from 0x010F
  (the R1-fix was previously unreachable because all test fixtures wrote at
  the default offset; added offset fixture to cover it).
- `model list --type text_encoders` now handles both legacy `[[values], {}]`
  and V3 `["COMBO", {"options": [...]}]` `/object_info` shapes. Previously
  the extractor silently returned `[]` for V3 loaders; confirmed on live
  TripleCLIPLoader.

**Top Major fixes shipped:**
- `ComfyWsClient.watch()` now re-raises socket timeouts as
  `ComfyConnectionError` (exit 2) instead of a bare `RuntimeError`. Added
  a `TestWsClient` class with 7 unit tests for terminator handling, error
  events, binary frames, and timeout.
- `queue wait --live` now checks `/history` BEFORE opening the websocket
  to close the race where a prompt completes before the client subscribes.
- `httpx.ReadTimeout`/`WriteTimeout`/`PoolTimeout` now caught on every
  command (previously only `ConnectError`/`ConnectTimeout`).
- Non-JSON 200 bodies (reverse-proxy HTML) now surface as `ComfyError`
  with a clear message instead of a raw `JSONDecodeError` traceback.
- Wiki `input-output.md` corrected: `output download` writes
  `<DIR>/<prompt_id>/<filename>`, not `<DIR>/<node_id>/<filename>`.

**Final tallies:**
- 188 tests passing, 1 skipped (integration test requires a ComfyUI-generated PNG
  on disk — unavailable because no checkpoints are installed locally).
- Tier 1: 170 mocked + Tier 2: 18 live-server + 1 Tier-3-like skip.
- R5 wiki execution: 69 documented CLI commands run against live
  127.0.0.1:8188 — 68 pass, 1 minor drift (fixed: `workflow validate`
  on non-JSON now exits 3 per wiki).
- 24/24 wiki URLs live, 0 broken links, 0 orphans.
