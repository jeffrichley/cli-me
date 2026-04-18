"""queue status — /queue (no id) or /history/<id> (with id)."""

from __future__ import annotations

import json
import sys
from typing import Optional

import httpx
from rich.console import Console
from rich.table import Table

from comfyui_cli.backend import (
    ComfyError,
    ComfyExecutionError,
    ComfyNotFoundError,
    classify_network_error,
    get_base_url,
    handle_http_errors,
    http_client,
)


_console = Console()


def _render_queue_table(data: dict) -> None:
    """Render /queue response as a table. Items are 5-tuples per queue-api.md."""
    table = Table(title="Queue", title_style="bold")
    table.add_column("status", style="dim")
    table.add_column("number", justify="right")
    table.add_column("prompt_id")
    table.add_column("nodes", justify="right")

    for item in data.get("queue_running") or []:
        number, prompt_id, prompt, _extra, _outputs = _unpack(item)
        node_count = len(prompt) if isinstance(prompt, dict) else 0
        table.add_row("running", str(number), str(prompt_id), str(node_count))

    for item in data.get("queue_pending") or []:
        number, prompt_id, prompt, _extra, _outputs = _unpack(item)
        node_count = len(prompt) if isinstance(prompt, dict) else 0
        table.add_row("pending", str(number), str(prompt_id), str(node_count))

    _console.print(table)


def _unpack(item: list) -> tuple:
    """Unpack a 5-tuple queue item defensively (pad with None if short)."""
    padded = list(item) + [None] * max(0, 5 - len(item))
    return tuple(padded[:5])


def _fetch_and_parse(url: Optional[str], path: str) -> tuple[httpx.Response, dict]:
    """Shared GET + JSON-parse helper for /queue and /history."""
    base = get_base_url(url)
    try:
        with http_client(base, timeout=30.0) as client:
            response = client.get(path)
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
            f"ComfyUI returned non-JSON response from {path}.",
            detail=str(exc),
        ) from exc

    return response, data


def run_status(
    *,
    prompt_id: Optional[str] = None,
    url: Optional[str] = None,
    json_output: bool = False,
) -> None:
    """Report queue contents (no id) or a specific prompt's status (with id).

    Raises:
        ComfyNotFoundError (exit 5): /history/<id> returned {} (unknown id).
        ComfyExecutionError (exit 4): status.status_str != 'success'.
        ComfyConnectionError (exit 2): server unreachable.
        ComfyError (exit 1): other non-2xx, malformed JSON.
    """
    if prompt_id is None:
        response, data = _fetch_and_parse(url, "/queue")
        if json_output:
            sys.stdout.write(response.text)
            sys.stdout.flush()
            return
        _render_queue_table(data)
        return

    # With prompt_id: /history/<id>
    response, data = _fetch_and_parse(url, f"/history/{prompt_id}")

    if json_output:
        sys.stdout.write(response.text)
        sys.stdout.flush()
        # For json, still check shape for exit code semantics
        if not data:
            raise ComfyNotFoundError(
                f"No history entry for prompt_id={prompt_id} (unknown or evicted)."
            )
        entry = data.get(prompt_id) or next(iter(data.values()), {})
        status_str = (entry.get("status") or {}).get("status_str", "")
        if status_str == "success":
            return
        raise ComfyExecutionError(
            f"Prompt {prompt_id} ended with status={status_str!r}.",
        )

    if not data:
        raise ComfyNotFoundError(
            f"No history entry for prompt_id={prompt_id} (unknown or evicted)."
        )

    entry = data.get(prompt_id) or next(iter(data.values()), {})
    status = entry.get("status") or {}
    status_str = status.get("status_str", "")

    if status_str == "success":
        _console.print(f"[green]success[/green] {prompt_id}")
        return

    # error path — collect exception info from messages
    detail = _extract_error_detail(status)
    raise ComfyExecutionError(
        f"Prompt {prompt_id} ended with status={status_str!r}.",
        detail=detail,
    )


def _extract_error_detail(status: dict) -> Optional[str]:
    """Pull the first execution_error exception_message from status.messages."""
    for event_name, payload in status.get("messages") or []:
        if event_name == "execution_error" and isinstance(payload, dict):
            msg = payload.get("exception_message")
            etype = payload.get("exception_type")
            if msg:
                return f"[{etype}] {msg}" if etype else str(msg)
    return None
