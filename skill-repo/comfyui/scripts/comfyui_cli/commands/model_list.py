"""model list — enumerate model files via /object_info and /embeddings.

Queries the ComfyUI server for each model type's loader node and extracts the
filename list from the node's `input.required.<param>` enum dropdown. For the
`embeddings` pseudo-type, falls back to the dedicated `/embeddings` endpoint.

See references/techniques/models-and-assets.md for the protocol details.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Iterable, Optional

import httpx
from rich.console import Console
from rich.table import Table

from comfyui_cli.backend import (
    ComfyError,
    ComfyValidationError,
    classify_network_error,
    get_base_url,
    handle_http_errors,
    http_client,
)


_console = Console()

# (NodeClass, input-param) pairs per model type. A type with multiple pairs is
# the union of all listed sources. `embeddings` is handled separately via the
# /embeddings HTTP endpoint — see _fetch_embeddings below.
TYPE_TO_NODES: dict[str, list[tuple[str, str]]] = {
    "checkpoints": [("CheckpointLoaderSimple", "ckpt_name")],
    "loras": [("LoraLoader", "lora_name")],
    "vae": [("VAELoader", "vae_name")],
    "controlnet": [("ControlNetLoader", "control_net_name")],
    "upscale_models": [("UpscaleModelLoader", "model_name")],
    "text_encoders": [
        ("CLIPLoader", "clip_name"),
        ("DualCLIPLoader", "clip_name1"),
        ("DualCLIPLoader", "clip_name2"),
        ("TripleCLIPLoader", "clip_name1"),
        ("TripleCLIPLoader", "clip_name2"),
        ("TripleCLIPLoader", "clip_name3"),
    ],
    "diffusion_models": [("UNETLoader", "unet_name")],
    "style_models": [("StyleModelLoader", "style_model_name")],
    "clip_vision": [("CLIPVisionLoader", "clip_name")],
    "hypernetworks": [("HypernetworkLoader", "hypernetwork_name")],
    "gligen": [("GLIGENLoader", "gligen_name")],
    "photomaker": [("PhotoMakerLoader", "photomaker_model_name")],
    "embeddings": [],  # uses /embeddings special-case
}

# Ordered list of types for the summary view (no --type). "embeddings" last.
_SUMMARY_ORDER: list[str] = [
    "checkpoints",
    "diffusion_models",
    "loras",
    "vae",
    "text_encoders",
    "clip_vision",
    "controlnet",
    "upscale_models",
    "style_models",
    "hypernetworks",
    "gligen",
    "photomaker",
    "embeddings",
]


def is_enum(values: Any) -> bool:
    """Return True if `values` is a dropdown enum rather than a typed socket.

    /object_info `input.required.<key>[0]` is either a list of dropdown values
    (filenames for loader nodes) or a *single-element* list containing a type
    name like `["LATENT"]`, `["MODEL"]`, `["CLIP"]`. The canonical extraction
    rule rejects the typed-socket shape — a single uppercase alphanumeric+
    underscore token — and accepts everything else.
    """
    if not isinstance(values, list) or not values:
        return False
    first = values[0]
    if (
        len(values) == 1
        and isinstance(first, str)
        and first.isupper()
        and first.replace("_", "").isalnum()
    ):
        return False
    return True


def _extract_filenames(node_body: dict, node_class: str, param: str) -> list[str]:
    """Pull the dropdown list for `param` out of one /object_info/<node> body.

    Handles BOTH the legacy and V3 COMBO shapes:

    - Legacy: ``[[filename1, filename2, ...], {...options...}]`` — first element
      is the list of values, second is the options dict.
    - V3 COMBO: ``["COMBO", {"options": [filename1, ...], "multiselect": ..., ...}]``
      — first element is the type string ``"COMBO"``, values live under
      ``spec[1]["options"]``. Emitted by ``_ComfyNodeInternal`` subclasses
      (e.g. ``TripleCLIPLoader``, ``QuadrupleCLIPLoader``) serialized via
      ``GET_NODE_INFO_V1()``.

    Returns [] if the node body doesn't contain either expected shape.
    """
    node = node_body.get(node_class)
    if not isinstance(node, dict):
        return []
    try:
        spec = node["input"]["required"][param]
    except (KeyError, TypeError):
        return []
    if not isinstance(spec, list) or not spec:
        return []
    first = spec[0]
    # V3 COMBO shape: first element is a type string, options live at spec[1].
    if isinstance(first, str):
        if len(spec) >= 2 and isinstance(spec[1], dict):
            options = spec[1].get("options")
            if isinstance(options, list):
                return [x for x in options if isinstance(x, str)]
        return []
    # Legacy shape: first element is the list of dropdown values (or a typed
    # socket like ["LATENT"] which is_enum rejects).
    if is_enum(first):
        return [x for x in first if isinstance(x, str)]
    return []


def _get_object_info(client: httpx.Client, node_class: str) -> Optional[dict]:
    """GET /object_info/<node_class>; return None on 404 (unknown node)."""
    response = client.get(f"/object_info/{node_class}")
    if response.status_code == 404:
        return None
    handle_http_errors(response)
    try:
        return response.json()
    except (json.JSONDecodeError, httpx.DecodingError) as exc:
        raise ComfyError(
            f"ComfyUI returned non-JSON for /object_info/{node_class}",
            detail=str(exc),
        ) from exc


def _fetch_embeddings(client: httpx.Client) -> list[str]:
    """GET /embeddings — returns a flat JSON list of filenames."""
    response = client.get("/embeddings")
    handle_http_errors(response)
    try:
        data = response.json()
    except (json.JSONDecodeError, httpx.DecodingError) as exc:
        raise ComfyError(
            "ComfyUI returned non-JSON for /embeddings",
            detail=str(exc),
        ) from exc
    if not isinstance(data, list):
        return []
    return [str(x) for x in data]


def fetch_filenames(client: httpx.Client, type_name: str) -> list[str]:
    """Return the deduplicated list of files for a single model type.

    Unknown types raise ComfyError(exit_code=3). Missing node classes (404) are
    skipped so older ComfyUI installs without TripleCLIPLoader still work.
    Order-preserving dedup so the first source wins.
    """
    if type_name not in TYPE_TO_NODES:
        raise ComfyValidationError(
            f"Unknown model type: {type_name}. "
            f"Known: {', '.join(sorted(TYPE_TO_NODES))}."
        )
    if type_name == "embeddings":
        return _fetch_embeddings(client)

    seen: set[str] = set()
    ordered: list[str] = []
    # Fetch each node class at most once — text_encoders re-uses DualCLIPLoader
    # and TripleCLIPLoader for multiple param names.
    node_cache: dict[str, Optional[dict]] = {}
    for node_class, param in TYPE_TO_NODES[type_name]:
        if node_class not in node_cache:
            node_cache[node_class] = _get_object_info(client, node_class)
        body = node_cache[node_class]
        if body is None:
            continue  # node class not present on this server
        for name in _extract_filenames(body, node_class, param):
            if name not in seen:
                seen.add(name)
                ordered.append(name)
    return ordered


def _emit_json(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def _render_single_type_table(type_name: str, files: list[str]) -> None:
    table = Table(title=f"{type_name} ({len(files)})", title_style="bold")
    table.add_column("filename")
    for f in files:
        table.add_row(f)
    _console.print(table)


def _render_summary_table(counts: dict[str, int]) -> None:
    table = Table(title="Models", title_style="bold")
    table.add_column("type")
    table.add_column("count", justify="right")
    for key in _SUMMARY_ORDER:
        if key in counts:
            table.add_row(key, str(counts[key]))
    _console.print(table)


def run_list(
    *,
    type_name: Optional[str],
    url: Optional[str],
    json_output: bool,
) -> None:
    """List model filenames for one type, or counts across all types.

    Raises:
        ComfyError(exit_code=3): unknown `type_name`
        ComfyConnectionError(2): server unreachable / timed out
        ComfyOriginError(2): 403 origin guard
        ComfyError(1): any other non-2xx or malformed response
    """
    if type_name is not None and type_name not in TYPE_TO_NODES:
        raise ComfyValidationError(
            f"Unknown model type: {type_name}. "
            f"Known: {', '.join(sorted(TYPE_TO_NODES))}.",
        )
    base = get_base_url(url)
    try:
        with http_client(base) as client:
            if type_name is not None:
                files = fetch_filenames(client, type_name)
                if json_output:
                    _emit_json({type_name: files})
                else:
                    _render_single_type_table(type_name, files)
                return

            # No --type: full summary of counts per known type.
            counts: dict[str, int] = {}
            for key in _SUMMARY_ORDER:
                counts[key] = len(fetch_filenames(client, key))
            if json_output:
                _emit_json(counts)
            else:
                _render_summary_table(counts)
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ) as exc:
        raise classify_network_error(exc, base) from exc


# Back-compat shim for the scaffolded entrypoint name.
def run_model_list(
    *,
    type: Optional[str] = None,  # noqa: A002 — param kept for Typer-compat
    url: Optional[str] = None,
    json_output: bool = False,
) -> None:
    run_list(type_name=type, url=url, json_output=json_output)
