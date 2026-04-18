"""model find — case-insensitive substring search across all model types."""

from __future__ import annotations

import json
import sys
from typing import Optional

import httpx
from rich.console import Console

from comfyui_cli.backend import (
    classify_network_error,
    get_base_url,
    http_client,
)
from comfyui_cli.commands.model_list import TYPE_TO_NODES, fetch_filenames


_console = Console()
_stderr = Console(stderr=True)


def _search(
    client: httpx.Client, needle: str
) -> dict[str, list[str]]:
    """Return {type: [matching filenames]} for each type with at least one match."""
    needle_l = needle.lower()
    results: dict[str, list[str]] = {}
    for type_name in TYPE_TO_NODES:
        files = fetch_filenames(client, type_name)
        hits = [f for f in files if needle_l in f.lower()]
        if hits:
            results[type_name] = hits
    return results


def _render_text(results: dict[str, list[str]]) -> None:
    for type_name in sorted(results):
        for filename in results[type_name]:
            _console.print(f"{type_name}: {filename}")


def run_find(
    *,
    name: str,
    url: Optional[str],
    json_output: bool,
) -> None:
    """Search every model type for a filename containing `name` (case-insensitive).

    Exit code is always 0 even when no matches are found — callers can detect
    "nothing found" from the JSON output's empty dict, or from the stderr
    "no matches" message in text mode.
    """
    base = get_base_url(url)
    try:
        with http_client(base) as client:
            results = _search(client, name)
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ) as exc:
        raise classify_network_error(exc, base) from exc

    if json_output:
        sys.stdout.write(json.dumps(results))
        sys.stdout.flush()
        if not results:
            _stderr.print("no matches")
        return

    if not results:
        _stderr.print("no matches")
        return
    _render_text(results)


# Back-compat shim for the scaffolded entrypoint name.
def run_model_find(
    *,
    name: str,
    url: Optional[str] = None,
    json_output: bool = False,
) -> None:
    run_find(name=name, url=url, json_output=json_output)
