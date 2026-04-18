"""Shared backend utilities for ComfyUI CLI.

- URL resolution (flag > env > default)
- httpx client factory with origin-guard header set
- Typed exception hierarchy and HTTP error handling
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import httpx
from rich.console import Console

DEFAULT_BASE_URL = "http://127.0.0.1:8188"


# --- Exception hierarchy ---------------------------------------------------


class ComfyError(Exception):
    """Base exception for ComfyUI CLI errors."""

    exit_code: int = 1

    def __init__(self, message: str, *, detail: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class ComfyConnectionError(ComfyError):
    """Connection refused / host unreachable / generic network failure."""

    exit_code = 2


class ComfyOriginError(ComfyError):
    """403 origin-guard rejection from ComfyUI server."""

    exit_code = 2


class ComfyValidationError(ComfyError):
    """400 with node_errors — workflow failed server-side validation."""

    exit_code = 3

    def __init__(
        self,
        message: str,
        *,
        node_errors: Optional[dict] = None,
        detail: Optional[str] = None,
    ) -> None:
        super().__init__(message, detail=detail)
        self.node_errors = node_errors or {}


class ComfyExecutionError(ComfyError):
    """Execution error surfaced via /ws `execution_error` event."""

    exit_code = 4


class ComfyNotFoundError(ComfyError):
    """404 from /view or missing prompt_id in /history."""

    exit_code = 5


# --- URL / client helpers --------------------------------------------------


def get_base_url(cli_url: Optional[str] = None) -> str:
    """Resolve the ComfyUI base URL.

    Precedence: --url flag > COMFY_URL env > default (127.0.0.1:8188).
    Trailing slashes are stripped.
    """
    url = cli_url or os.environ.get("COMFY_URL") or DEFAULT_BASE_URL
    return url.rstrip("/")


def http_client(base_url: str, timeout: float = 30.0) -> httpx.Client:
    """Create a pre-configured httpx.Client for the ComfyUI server.

    Sets the `Origin` header to match `base_url` so ComfyUI's origin-guard
    (enabled when the server is bound to a public interface) accepts the
    request. See references/gotchas.md and techniques/server-info-and-errors.md.
    """
    return httpx.Client(
        base_url=base_url,
        timeout=timeout,
        headers={"Origin": base_url},
    )


# --- HTTP error handling ---------------------------------------------------


def classify_network_error(exc: Exception, base_url: str) -> ComfyConnectionError:
    """Map an httpx network exception to a ComfyConnectionError with a helpful message.

    Distinguishes "server not running" (ConnectError / ConnectTimeout) from
    "server too slow" (ReadTimeout / WriteTimeout / PoolTimeout) so users know
    whether to start the server or bump --timeout.
    """
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
        return ComfyConnectionError(
            f"ComfyUI is not running at {base_url}",
            detail=str(exc),
        )
    if isinstance(exc, (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)):
        return ComfyConnectionError(
            f"ComfyUI timed out responding at {base_url} (consider a longer --timeout)",
            detail=str(exc),
        )
    # Fallback — unclassified httpx transport error
    return ComfyConnectionError(
        f"Network error talking to ComfyUI at {base_url}",
        detail=str(exc),
    )


def handle_http_errors(response: httpx.Response) -> None:
    """Raise the right ComfyError subclass for a non-2xx response.

    No-op on success. Caller should still `response.raise_for_status()`-check
    after this returns if additional handling is needed.
    """
    if response.is_success:
        return

    status = response.status_code
    # Attempt to parse JSON body for richer error messages
    body_text: str = ""
    body_json: Optional[dict] = None
    try:
        body_json = response.json()
        body_text = response.text
    except Exception:
        body_text = response.text

    if status == 403:
        raise ComfyOriginError(
            "ComfyUI rejected the request (403). Likely origin-guard; "
            "ensure --url matches what ComfyUI is bound to.",
            detail=body_text,
        )
    if status == 404:
        raise ComfyNotFoundError(
            f"Not found: {response.request.url}",
            detail=body_text,
        )
    if status == 400 and isinstance(body_json, dict) and "node_errors" in body_json:
        raise ComfyValidationError(
            body_json.get("error", {}).get("message", "Workflow validation failed"),
            node_errors=body_json.get("node_errors") or {},
            detail=body_text,
        )
    raise ComfyError(
        f"ComfyUI returned HTTP {status} for {response.request.url}",
        detail=body_text,
    )


# --- Pretty error printing -------------------------------------------------

_stderr = Console(stderr=True)


def print_error_and_exit(err: ComfyError) -> None:
    """Print a ComfyError to stderr via Rich and exit with its exit_code."""
    _stderr.print(f"[bold red]error:[/bold red] {err.message}")
    if err.detail:
        _stderr.print(f"[dim]{err.detail}[/dim]")
    sys.exit(err.exit_code)
