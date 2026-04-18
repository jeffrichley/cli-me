# CLI Interface (main.py flags)

ComfyUI's launch flags are declared in `comfy/cli_args.py` (one flat `argparse.ArgumentParser`) and consumed from a shared `args` singleton throughout `main.py`, `server.py`, and the rest of the tree. Every flag below has a `file:line` pointer into `comfy/cli_args.py`.

## Networking

| flag | type / default | purpose | line |
|------|----------------|---------|------|
| `--listen [IP]` | str, default `127.0.0.1` (const `0.0.0.0,::` when bare) | Comma-separated list of IPs to bind. Bare `--listen` means "all ipv4 and ipv6". | `38` |
| `--port PORT` | int, default `8188` | Listen port. | `39` |
| `--tls-keyfile PATH` | str | Enables TLS; must pair with `--tls-certfile`. | `40` |
| `--tls-certfile PATH` | str | TLS cert; must pair with `--tls-keyfile`. | `41` |
| `--enable-cors-header [ORIGIN]` | str, const `*` | Install a CORS middleware. Without this, origin-only middleware rejects cross-site requests to loopback. | `42` |
| `--max-upload-size MB` | float, default `100` | Max request body in MB (`server.py:234`). | `43` |
| `--enable-compress-response-body` | flag | Enable gzip compression middleware for JSON/text responses. | `227` |

Note: there is **no** `--max-queue-size` flag in v0.19.0. The queue size is effectively unbounded (backed by a `heapq` list in `execution.PromptQueue`, `execution.py:1188-1329`).

## Directories

| flag | purpose | line |
|------|---------|------|
| `--base-directory PATH` | Override base dir for models/input/output/temp/user/custom_nodes. | `45` |
| `--extra-model-paths-config PATH [PATH ...]` | Append `extra_model_paths.yaml` files. Repeatable (`action='append'`, `nargs='+'`). Applied in `main.py:101-103`. | `46` |
| `--output-directory PATH` | Override output dir. Applied in `main.py:106-109`. | `47` |
| `--temp-directory PATH` | Override temp dir (applied late in `main.py:447-450`). | `48` |
| `--input-directory PATH` | Override input dir. Applied in `main.py:119-122`. | `49` |
| `--user-directory PATH` | Override user dir (validated via `is_valid_directory`). | `225` |
| `--front-end-root PATH` | Serve the frontend from a local directory instead of downloading a release. | `218-223` |
| `--front-end-version STR` | `owner/repo@version` spec for the frontend build to download (default `comfyanonymous/ComfyUI@latest`). | `194-206` |

## Launch / UI

| flag | purpose | line |
|------|---------|------|
| `--auto-launch` | Open the default browser on startup. Implicitly set by `--windows-standalone-build` (`cli_args.py:247-248`). | `50` |
| `--disable-auto-launch` | Force-disable auto-launch. | `51` |
| `--windows-standalone-build` | Bundle-specific conveniences (implies `--auto-launch`). | `178` |
| `--dont-print-server` | Suppress the "Starting server" / "To see the GUI" banner. Wired via `verbose=not args.dont_print_server` in `main.py:500`. | `176` |
| `--quick-test-for-ci` | Exit immediately after setup; used by CI smoke tests. | `177` |

## Device selection

| flag | purpose | line |
|------|---------|------|
| `--cuda-device DEVICE_ID` | Sets `CUDA_VISIBLE_DEVICES` / `HIP_VISIBLE_DEVICES` / `ASCEND_RT_VISIBLE_DEVICES`. | `52` |
| `--default-device DEFAULT_DEVICE_ID` | Reorder visible devices so this one is default. | `53` |
| `--cpu` | Mutually exclusive with the VRAM modes below; run everything on CPU. | `147` |
| `--gpu-only` | Keep text encoders/CLIP on the GPU too. | `142` |
| `--highvram` | Keep models resident in VRAM after use. | `143` |
| `--normalvram` | Force normal VRAM mode (overrides auto-lowvram). | `144` |
| `--lowvram` | Split the unet across CPU/GPU. | `145` |
| `--novram` | Even more aggressive than lowvram. | `146` |
| `--reserve-vram GB` | Reserve VRAM for other apps. | `149` |
| `--directml [DEVICE]` | Use torch-directml on the given device. | `90` |
| `--oneapi-device-selector SELECTOR` | Sets `ONEAPI_DEVICE_SELECTOR`. | `92` |
| `--disable-ipex-optimize` | Skip Intel IPEX optimize step. | `93` |
| `--cuda-malloc` / `--disable-cuda-malloc` | Mutually exclusive cudaMallocAsync toggles. | `55-56` |
| `--supports-fp8-compute` | Pretend the device supports fp8 compute. | `94` |

## Precision / performance

`--force-fp32` / `--force-fp16`: global precision overrides (mutually exclusive), `cli_args.py:59-61`.

Unet precision (mutually exclusive, `cli_args.py:63-70`): `--fp32-unet`, `--fp64-unet`, `--bf16-unet`, `--fp16-unet`, `--fp8_e4m3fn-unet`, `--fp8_e5m2-unet`, `--fp8_e8m0fnu-unet`.

VAE precision (mutually exclusive, `cli_args.py:72-75`): `--fp16-vae`, `--fp32-vae`, `--bf16-vae`. Plus `--cpu-vae` at `:77`.

Text encoder precision (mutually exclusive, `cli_args.py:79-84`): `--fp8_e4m3fn-text-enc`, `--fp8_e5m2-text-enc`, `--fp16-text-enc`, `--fp32-text-enc`, `--bf16-text-enc`.

Other:

- `--fp16-intermediates` — fp16 for inter-node tensors (`:86`).
- `--force-channels-last` — prefer channels-last layout (`:88`).
- `--fast [FEATURE ...]` — enable one or more of `fp16_accumulation`, `fp8_matrix_mult`, `cublas_ops`, `autotune`; bare `--fast` enables all (`:163-169`, resolved `:258-265`).
- `--disable-pinned-memory` (`:171`), `--mmap-torch-files` (`:173`), `--disable-mmap` (`:174`).
- `--force-non-blocking` (`:156`), `--disable-smart-memory` (`:160`), `--deterministic` (`:161`).
- `--default-hashing-function {md5,sha1,sha256,sha512}` (default `sha256`, `:158`).

Attention kernels (mutually exclusive, `cli_args.py:121-126`): `--use-split-cross-attention`, `--use-quad-cross-attention`, `--use-pytorch-cross-attention`, `--use-sage-attention`, `--use-flash-attention`. Plus `--disable-xformers` (`:128`), `--force-upcast-attention` / `--dont-upcast-attention` (`:131-132`).

Async offload: `--async-offload [NUM_STREAMS]` (default 2 when bare, `:151`), `--disable-async-offload` (`:152`).

Dynamic VRAM: `--enable-dynamic-vram` (`:154`), `--disable-dynamic-vram` (`:153`). See `enables_dynamic_vram()` (`:267-270`) for the auto-enable logic.

## Cache control

Mutually exclusive group (`cli_args.py:115-119`), read by `main.py:278-289`:

- `--cache-classic` — aggressive whole-graph caching (old default).
- `--cache-lru N` — LRU with up to N cached node results.
- `--cache-ram [GB]` — RAM-pressure caching; bare flag means auto (25% of system RAM, min 4 GB, max 32 GB; `main.py:278-280`).
- `--cache-none` — no caching; re-execute every node each run.

## Preview

- `--preview-method {none,auto,latent2rgb,taesd}` — default preview strategy (`:109`).
- `--preview-size INT` — max preview image side (default 512, `:111`).

## Nodes and extensions

- `--disable-all-custom-nodes` — skip all custom node packs (`:181`).
- `--whitelist-custom-nodes NAME [NAME ...]` — load only these even with `--disable-all-custom-nodes` (`:182`).
- `--disable-api-nodes` — skip API nodes; also installs CSP middleware blocking outbound network calls from the frontend (`:183`, triggers `create_block_external_middleware()` in `server.py:228-229`).
- `--enable-manager` — load `comfyui-manager` (`:135`).
- `--disable-manager-ui` (`:137`), `--enable-manager-legacy-ui` (`:138`) — mutually exclusive manager UI toggles.

## Logging

- `--verbose [LEVEL]` — `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, `CRITICAL`; bare flag = `DEBUG` (`:187`).
- `--log-stdout` — pipe logs to stdout (default is stderr, `:188`).

## Miscellaneous

- `--multi-user` — per-user isolated storage (`:185`).
- `--disable-metadata` — don't embed prompt metadata in saved images (`:180`).
- `--comfy-api-base URL` — override the `api.comfy.org` base URL (`:229-234`).
- `--database-url URL` — SQLAlchemy URL; default is a SQLite file at `<ComfyUI>/user/comfyui.db` (`:236-239`).
- `--enable-assets` — activate the asset database/API and background scanner (`:240`).

## Surprises

- **No `--max-queue-size`.** The task said to cover it, but v0.19.0 has no such flag — the queue is unbounded.
- **Flags live in `comfy/cli_args.py`, not `main.py`.** `main.py` imports the already-parsed `args` singleton (`main.py:10`). This matters for wrappers: you can re-parse by constructing a new `ArgumentParser` only if you mutate `comfy.options.args_parsing` first (`cli_args.py:242-245`).
- **`--listen` without an argument flips to dual-stack.** Bare `--listen` binds `0.0.0.0,::` (const in `:38`), not `0.0.0.0`. That dual-stack default trips up clients that assume one address.
- **`--fast` with no args enables every optimization**, including unstable ones (`cli_args.py:260-262`: `args.fast = set(PerformanceFeature)`). Never pass bare `--fast` in a production wrapper unless you want to opt into all of them.
- **`--force-fp16` implies `--fp16-unet`** silently (`cli_args.py:253-254`).
- **`--windows-standalone-build` implies `--auto-launch`** (`cli_args.py:247-248`), which pops a browser. Strip it from headless wrappers.
- **`--extra-model-paths-config` is `action='append'` with `nargs='+'`** so each occurrence adds a list, and `main.py:101-103` flattens with `itertools.chain(*args.extra_model_paths_config)`. You can pass it multiple times *and* give multiple paths per occurrence.
- **CORS is off by default but the origin guard is on.** Not setting `--enable-cors-header` installs `create_origin_only_middleware` (`server.py:220-226`), which returns 403 for cross-origin requests to loopback. Any wrapper that talks to a remote ComfyUI has to either set CORS or run same-origin.
