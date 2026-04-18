"""queue clear — POST /queue {"clear": true}."""

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


def run_clear(*, url: Optional[str] = None) -> None:
    """Drop everything pending in the queue; print `cleared N pending`.

    Counts pending via GET /queue first, then POST /queue {"clear": true}.
    """
    base = get_base_url(url)

    try:
        with http_client(base, timeout=10.0) as client:
            get_resp = client.get("/queue")
            handle_http_errors(get_resp)

            try:
                data = get_resp.json()
            except (json.JSONDecodeError, httpx.DecodingError) as exc:
                raise ComfyError(
                    "ComfyUI returned non-JSON response from /queue.",
                    detail=str(exc),
                ) from exc
            pending_count = len(data.get("queue_pending") or [])

            post_resp = client.post("/queue", json={"clear": True})
            handle_http_errors(post_resp)
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ) as exc:
        raise classify_network_error(exc, base) from exc

    _console.print(f"cleared {pending_count} pending")
