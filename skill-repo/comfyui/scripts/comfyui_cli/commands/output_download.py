"""output download — resolve /history then GET /view per output image."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console
from rich.table import Table

from comfyui_cli.backend import (
    ComfyError,
    ComfyNotFoundError,
    classify_network_error,
    get_base_url,
    handle_http_errors,
    http_client,
)


_console = Console()
_stderr = Console(stderr=True)

DEFAULT_DIR = Path("./comfy_outputs")
CHUNK_SIZE = 64 * 1024


def _iter_refs(outputs: dict):
    """Yield every `{filename, subfolder, type}` ref from the outputs dict.

    Iterates all list-valued keys under each node (wiki: images, gifs, etc.)
    and skips scalar siblings like `animated: [true]` when they are not dicts.
    """
    for node_id, node_out in (outputs or {}).items():
        if not isinstance(node_out, dict):
            continue
        for key, refs in node_out.items():
            if not isinstance(refs, list):
                continue
            if key == "animated":
                continue
            for ref in refs:
                if not isinstance(ref, dict) or "filename" not in ref:
                    continue
                yield node_id, ref


def run_download(
    *,
    prompt_id: str,
    dest_dir: Optional[Path] = None,
    url: Optional[str] = None,
    json_output: bool = False,
) -> None:
    """Download every output image for a completed prompt.

    GET /history/<prompt_id>, then for each output ref GET /view and save to
    `dest_dir/<prompt_id>/<filename>`. A single 404 is logged and skipped;
    other /view errors also log and continue. An empty /history response for
    the prompt_id raises ComfyNotFoundError (exit 5).

    Raises:
        ComfyNotFoundError (exit 5): prompt_id not found in /history.
        ComfyConnectionError (exit 2): server unreachable.
        ComfyError (exit 1): other failures.
    """
    base = get_base_url(url)
    root_dir = Path(dest_dir) if dest_dir is not None else DEFAULT_DIR

    try:
        with http_client(base, timeout=30.0) as client:
            history_resp = client.get(f"/history/{prompt_id}")
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ) as exc:
        raise classify_network_error(exc, base) from exc

    handle_http_errors(history_resp)

    try:
        history = history_resp.json()
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

    target = root_dir / prompt_id
    target.mkdir(parents=True, exist_ok=True)

    saved: list[dict] = []
    skipped: list[dict] = []

    try:
        with http_client(base, timeout=120.0) as client:
            for node_id, ref in _iter_refs(outputs):
                filename = ref["filename"]
                params = {
                    "filename": filename,
                    "subfolder": ref.get("subfolder", "") or "",
                    "type": ref.get("type", "output") or "output",
                }
                try:
                    resp = client.get("/view", params=params)
                except (
                    httpx.ConnectError,
                    httpx.ConnectTimeout,
                    httpx.ReadTimeout,
                    httpx.WriteTimeout,
                    httpx.PoolTimeout,
                ) as exc:
                    _stderr.print(
                        f"[yellow]warn:[/yellow] network error fetching "
                        f"{filename}: {exc}"
                    )
                    skipped.append(
                        {"node_id": node_id, "filename": filename, "reason": str(exc)}
                    )
                    continue

                if resp.status_code == 404:
                    _stderr.print(
                        f"[yellow]warn:[/yellow] /view returned 404 for "
                        f"{filename}; skipping"
                    )
                    skipped.append(
                        {"node_id": node_id, "filename": filename, "reason": "404"}
                    )
                    continue
                if not resp.is_success:
                    _stderr.print(
                        f"[yellow]warn:[/yellow] /view returned "
                        f"{resp.status_code} for {filename}; skipping"
                    )
                    skipped.append(
                        {
                            "node_id": node_id,
                            "filename": filename,
                            "reason": f"HTTP {resp.status_code}",
                        }
                    )
                    continue

                out_path = target / filename
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(resp.content)
                saved.append(
                    {
                        "node_id": node_id,
                        "filename": filename,
                        "path": str(out_path),
                        "size": out_path.stat().st_size,
                    }
                )
    except httpx.HTTPError as exc:
        raise ComfyError(
            f"Error while downloading outputs: {exc}", detail=str(exc)
        ) from exc

    if json_output:
        sys.stdout.write(
            json.dumps(
                {"prompt_id": prompt_id, "saved": saved, "skipped": skipped},
                indent=2,
            )
        )
        sys.stdout.write("\n")
        sys.stdout.flush()
        return

    if not saved and not skipped:
        _console.print(
            f"[dim](no outputs found for prompt_id {prompt_id})[/dim]"
        )
        return

    table = Table(title=f"Downloaded outputs for {prompt_id}", title_style="bold")
    table.add_column("Path")
    table.add_column("Size", justify="right")
    for item in saved:
        table.add_row(item["path"], f"{item['size']:,}")
    _console.print(table)

    if skipped:
        _console.print(f"[yellow]skipped {len(skipped)} files[/yellow]")
