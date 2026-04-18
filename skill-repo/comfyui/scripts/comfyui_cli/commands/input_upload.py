"""input upload — POST /upload/image; print {name, subfolder, type}."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console

from comfyui_cli.backend import (
    ComfyError,
    ComfyValidationError,
    classify_network_error,
    get_base_url,
    handle_http_errors,
    http_client,
)


_console = Console()


def _validate_subfolder(subfolder: Optional[str]) -> None:
    """Client-side check: reject `..` traversal. Wiki gotcha #3 / #8."""
    if subfolder is None or subfolder == "":
        return
    # Block any `..` path component in the subfolder
    parts = subfolder.replace("\\", "/").split("/")
    if any(p == ".." for p in parts):
        raise ComfyValidationError(
            f"Subfolder may not contain '..': {subfolder!r}. "
            "Relative-escape paths are rejected client-side."
        )


def run_upload(
    *,
    file: Path,
    subfolder: Optional[str] = None,
    overwrite: bool = False,
    url: Optional[str] = None,
    json_output: bool = False,
) -> None:
    """Upload a local image to ComfyUI's /input directory.

    POSTs multipart/form-data to /upload/image with explicit `type=input`.
    Prints the server response JSON `{"name", "subfolder", "type"}`. The
    returned `name` may differ from the local filename on collision-rename
    (wiki gotcha #2) — callers MUST use the server's `name`.

    Raises:
        ComfyValidationError: local `..` traversal in subfolder (exit 3)
        ComfyConnectionError: server unreachable (exit 2)
        ComfyOriginError: 403 origin guard (exit 2)
        ComfyNotFoundError: file doesn't exist locally (exit 5)
        ComfyError: any other non-2xx or malformed response (exit 1)
    """
    _validate_subfolder(subfolder)

    file = Path(file)
    if not file.is_file():
        raise ComfyError(
            f"File not found: {file}",
            detail="Pass a path to an existing file.",
        )

    base = get_base_url(url)

    # Multipart fields — strings, not Python bools. Wiki: server parses `"true"`.
    data = {
        "type": "input",
        "overwrite": "true" if overwrite else "false",
    }
    if subfolder:
        data["subfolder"] = subfolder

    try:
        with file.open("rb") as fh:
            files = {"image": (file.name, fh, "application/octet-stream")}
            try:
                with http_client(base, timeout=60.0) as client:
                    response = client.post(
                        "/upload/image", data=data, files=files
                    )
            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
            ) as exc:
                raise classify_network_error(exc, base) from exc
    except OSError as exc:
        raise ComfyError(
            f"Failed to read {file}: {exc}", detail=str(exc)
        ) from exc

    handle_http_errors(response)

    try:
        body = response.json()
    except (json.JSONDecodeError, httpx.DecodingError) as exc:
        raise ComfyError(
            "ComfyUI returned a non-JSON response from /upload/image.",
            detail=str(exc),
        ) from exc

    if json_output:
        sys.stdout.write(json.dumps(body, indent=2))
        sys.stdout.write("\n")
        sys.stdout.flush()
    else:
        sys.stdout.write(json.dumps(body))
        sys.stdout.write("\n")
        sys.stdout.flush()
