"""queue free — POST /free to reclaim VRAM / system memory."""

from __future__ import annotations

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


_stderr = Console(stderr=True)
_console = Console()


def run_free(
    *,
    url: Optional[str] = None,
    unload_models: bool = False,
    free_memory: bool = False,
) -> None:
    """Unload models and/or free cached memory via POST /free.

    Both flags default to False per the /free API. If neither is set, warn
    to stderr and exit 1 — the call would be a server-side no-op.
    """
    if not unload_models and not free_memory:
        raise ComfyError(
            "No flags set \u2014 --free is a no-op. "
            "Pass --unload-models and/or --free-memory.",
        )

    base = get_base_url(url)
    payload = {
        "unload_models": bool(unload_models),
        "free_memory": bool(free_memory),
    }

    try:
        with http_client(base, timeout=10.0) as client:
            response = client.post("/free", json=payload)
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ) as exc:
        raise classify_network_error(exc, base) from exc

    handle_http_errors(response)

    flags = []
    if unload_models:
        flags.append("unload_models")
    if free_memory:
        flags.append("free_memory")
    _console.print(f"ok ({', '.join(flags)})")
