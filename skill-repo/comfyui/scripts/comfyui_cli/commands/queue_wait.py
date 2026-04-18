"""queue wait — poll /history or consume /ws until prompt_id finishes."""

from __future__ import annotations

import json
import sys
import time
from typing import Optional

import httpx
from rich.console import Console

from comfyui_cli.backend import (
    ComfyError,
    ComfyExecutionError,
    classify_network_error,
    get_base_url,
    handle_http_errors,
    http_client,
)


_stderr = Console(stderr=True)


# Poll interval for non-live mode. Overridden by tests via monkeypatch for speed.
POLL_INTERVAL: float = 1.0


def _extract_error_detail(status: dict) -> Optional[str]:
    """Return a human-friendly error detail from status.messages, if any."""
    for event_name, payload in status.get("messages") or []:
        if event_name == "execution_error" and isinstance(payload, dict):
            msg = payload.get("exception_message")
            etype = payload.get("exception_type")
            if msg:
                return f"[{etype}] {msg}" if etype else str(msg)
    return None


def _poll_wait(
    *, prompt_id: str, url: Optional[str], timeout: float
) -> None:
    """Poll GET /history/<prompt_id> every POLL_INTERVAL until it appears."""
    base = get_base_url(url)
    start = time.monotonic()
    deadline = start + float(timeout) if timeout else None

    with http_client(base, timeout=10.0) as client:
        while True:
            try:
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
                data = response.json()
            except (json.JSONDecodeError, httpx.DecodingError) as exc:
                raise ComfyError(
                    "ComfyUI returned non-JSON response from /history.",
                    detail=str(exc),
                ) from exc

            if data:
                entry = data.get(prompt_id) or next(iter(data.values()), {})
                status = entry.get("status") or {}
                status_str = status.get("status_str", "")
                if status_str == "success":
                    _stderr.print()  # newline after dots
                    return
                # Non-success: surface as execution error.
                detail = _extract_error_detail(status)
                _stderr.print()
                raise ComfyExecutionError(
                    f"Prompt {prompt_id} ended with status={status_str!r}.",
                    detail=detail,
                )

            # Emit a dot per poll.
            _stderr.print(".", end="")

            if deadline is not None and time.monotonic() >= deadline:
                _stderr.print()
                raise ComfyError(
                    f"Timed out waiting for prompt_id={prompt_id} after {timeout}s",
                )

            time.sleep(POLL_INTERVAL)


def _check_history_once(
    *, prompt_id: str, base: str
) -> Optional[dict]:
    """Return the /history entry status dict if present, else None.

    Used by --live to avoid a race where the prompt finishes before the
    websocket connects. Network errors are classified; a missing entry
    (empty dict) returns None.
    """
    with http_client(base, timeout=10.0) as client:
        try:
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
        data = response.json()
    except (json.JSONDecodeError, httpx.DecodingError) as exc:
        raise ComfyError(
            "ComfyUI returned non-JSON response from /history.",
            detail=str(exc),
        ) from exc

    if not data:
        return None
    entry = data.get(prompt_id) or next(iter(data.values()), {})
    return entry.get("status") or {}


def _live_wait(
    *, prompt_id: str, url: Optional[str], timeout: float, client_id: Optional[str]
) -> None:
    """Stream /ws events; render per-node progress; terminate on success/error.

    Before connecting to the websocket, this checks /history once to cover the
    race where the prompt finishes between /prompt and /ws connect. If the
    history entry is already present we short-circuit and never open the ws.
    """
    # Deferred import so that test modules that never invoke --live don't
    # need the websocket-client install wired into the sys.path yet.
    from comfyui_cli.ws_client import ComfyWsClient

    base = get_base_url(url)

    # Race guard: if the prompt already finished, don't connect to ws.
    status = _check_history_once(prompt_id=prompt_id, base=base)
    if status is not None:
        status_str = status.get("status_str", "")
        if status_str == "success":
            return
        detail = _extract_error_detail(status)
        raise ComfyExecutionError(
            f"Prompt {prompt_id} ended with status={status_str!r}.",
            detail=detail,
        )

    ws_client = ComfyWsClient(base, client_id=client_id)
    ws_client.connect(timeout=timeout)

    try:
        result = ws_client.watch(prompt_id=prompt_id, timeout=timeout)
    finally:
        ws_client.close()

    status_str = result.get("status_str", "")
    if status_str == "success":
        return
    raise ComfyExecutionError(
        f"Prompt {prompt_id} ended with status={status_str!r}.",
        detail=result.get("detail"),
    )


def run_wait(
    *,
    prompt_id: str,
    url: Optional[str] = None,
    timeout: float = 600.0,
    live: bool = False,
    client_id: Optional[str] = None,
) -> None:
    """Block until prompt_id completes; with --live, stream /ws progress.

    Raises:
        ComfyExecutionError (exit 4): prompt ended with non-success status.
        ComfyError (exit 1): timed out waiting.
        ComfyConnectionError (exit 2): server unreachable.
    """
    if live:
        _live_wait(
            prompt_id=prompt_id,
            url=url,
            timeout=timeout,
            client_id=client_id,
        )
        return

    _poll_wait(prompt_id=prompt_id, url=url, timeout=timeout)
