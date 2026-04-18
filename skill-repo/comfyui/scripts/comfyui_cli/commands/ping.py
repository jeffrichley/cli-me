"""server ping — GET /system_stats, print ok + version/device summary."""

from __future__ import annotations

import json
from typing import Optional

import httpx
from rich.console import Console

from comfyui_cli.backend import (
    ComfyError,
    classify_network_error,
    get_base_url,
    handle_http_errors,
    http_client,
)


_console = Console()


def _device_summary(devices: list[dict]) -> str:
    """Short one-liner summary of the first device, for the ping line."""
    if not devices:
        return "no devices"
    dev = devices[0]
    dev_type = dev.get("type", "?")
    name = dev.get("name", "?")
    # CUDA entries look like "cuda:0 NVIDIA ... : cudaMallocAsync"; trim the
    # trailing " : cudaMallocAsync" suffix. For non-CUDA (name already starts
    # with the type), don't prefix `dev_type` again to avoid "cuda cuda:0 ..."
    if " : " in name:
        name = name.split(" : ", 1)[0]
    if name.lower().startswith(f"{dev_type.lower()}:") or name.lower() == dev_type.lower():
        return name
    return f"{dev_type} {name}"


def run_ping(*, url: Optional[str] = None, timeout: float = 10.0) -> None:
    """Ping the ComfyUI server and print `ok (version — device)` on success.

    Raises:
        ComfyConnectionError: server unreachable or timed out (exit 2)
        ComfyOriginError: 403 origin guard (exit 2)
        ComfyError: any other non-2xx or malformed response (exit 1)
    """
    base = get_base_url(url)
    try:
        with http_client(base, timeout=timeout) as client:
            response = client.get("/system_stats")
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ) as exc:
        raise classify_network_error(exc, base) from exc

    handle_http_errors(response)

    try:
        data = response.json()
    except (json.JSONDecodeError, httpx.DecodingError) as exc:
        raise ComfyError(
            "ComfyUI returned a non-JSON response (status 200). "
            "This usually means a reverse proxy is intercepting — check your --url.",
            detail=str(exc),
        ) from exc

    system = data.get("system", {}) or {}
    devices = data.get("devices", []) or []

    version = system.get("comfyui_version", "?")
    device_name = _device_summary(devices)

    _console.print(
        f"ok (ComfyUI {version} \u2014 {device_name})"
    )
