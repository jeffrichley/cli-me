"""output show — JSON dump of the outputs section from /history/<prompt_id>."""

from __future__ import annotations

import json
import sys
from typing import Optional

import httpx
from rich.console import Console

from comfyui_cli.backend import (
    ComfyError,
    ComfyNotFoundError,
    classify_network_error,
    get_base_url,
    handle_http_errors,
    http_client,
)


_console = Console()


def run_show(
    *,
    prompt_id: str,
    url: Optional[str] = None,
    json_output: bool = False,
) -> None:
    """Print the `outputs` dict from /history/<prompt_id> as JSON.

    Raises:
        ComfyNotFoundError (exit 5): prompt_id not present in /history response.
        ComfyConnectionError (exit 2): server unreachable.
        ComfyError (exit 1): other failures.
    """
    base = get_base_url(url)

    try:
        with http_client(base, timeout=30.0) as client:
            response = client.get(f"/history/{prompt_id}")
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
        history = response.json()
    except (json.JSONDecodeError, httpx.DecodingError) as exc:
        raise ComfyError(
            "ComfyUI returned a non-JSON response from /history.",
            detail=str(exc),
        ) from exc

    entry = history.get(prompt_id) if isinstance(history, dict) else None
    if not entry:
        raise ComfyNotFoundError(
            f"prompt_id not found in /history: {prompt_id!r}",
            detail="The prompt may not have completed, or the id is wrong.",
        )

    outputs = entry.get("outputs", {}) or {}

    # `json_output` toggles pretty-print vs compact. We never print the full
    # entry — only the outputs section (wiki: callers want the file refs).
    if json_output:
        sys.stdout.write(json.dumps(outputs, indent=2))
    else:
        sys.stdout.write(json.dumps(outputs))
    sys.stdout.write("\n")
    sys.stdout.flush()
