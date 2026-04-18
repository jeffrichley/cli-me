"""server info — pretty-print /system_stats as table or raw JSON."""

from __future__ import annotations

import json
import sys
from typing import Optional

import httpx
from rich.console import Console
from rich.table import Table

from comfyui_cli.backend import (
    ComfyError,
    classify_network_error,
    get_base_url,
    handle_http_errors,
    http_client,
)


_console = Console()


def _bytes_to_gib(n: int | float | None) -> str:
    """Format a byte count as GiB with one decimal place."""
    if n is None:
        return "?"
    try:
        gib = float(n) / (1024**3)
    except (TypeError, ValueError):
        return "?"
    return f"{gib:.1f} GiB"


def _short_python_version(v: str) -> str:
    """'3.12.10 (main, ...)' -> '3.12.10'."""
    if not v:
        return "?"
    return v.split(" ", 1)[0]


def _render_table(data: dict) -> None:
    system = data.get("system", {}) or {}
    devices = data.get("devices", []) or []

    # System table
    sys_table = Table(title="System", show_header=False, title_style="bold")
    sys_table.add_column("Field", style="dim")
    sys_table.add_column("Value")
    sys_table.add_row("OS", str(system.get("os", "?")))
    sys_table.add_row("ComfyUI", str(system.get("comfyui_version", "?")))
    sys_table.add_row("Python", _short_python_version(system.get("python_version", "")))
    sys_table.add_row("PyTorch", str(system.get("pytorch_version", "?")))
    ram_free = _bytes_to_gib(system.get("ram_free"))
    ram_total = _bytes_to_gib(system.get("ram_total"))
    sys_table.add_row("RAM", f"{ram_free} free / {ram_total}")
    sys_table.add_row(
        "Embedded Python",
        "yes" if system.get("embedded_python") else "no",
    )
    argv = system.get("argv") or []
    sys_table.add_row("Launch args", " ".join(str(a) for a in argv) or "(none)")

    _console.print(sys_table)

    # Devices table
    dev_table = Table(title="Devices", title_style="bold")
    dev_table.add_column("Idx", justify="right")
    dev_table.add_column("Type")
    dev_table.add_column("Name")
    dev_table.add_column("VRAM (free / total)")
    dev_table.add_column("Torch VRAM (free / total)")
    for dev in devices:
        idx = dev.get("index")
        idx_str = str(idx) if idx is not None else "-"
        dev_type = str(dev.get("type", "?"))
        dev_name = str(dev.get("name", "?"))
        vram = (
            f"{_bytes_to_gib(dev.get('vram_free'))} / "
            f"{_bytes_to_gib(dev.get('vram_total'))}"
        )
        torch_vram = (
            f"{_bytes_to_gib(dev.get('torch_vram_free'))} / "
            f"{_bytes_to_gib(dev.get('torch_vram_total'))}"
        )
        dev_table.add_row(idx_str, dev_type, dev_name, vram, torch_vram)
    _console.print(dev_table)


def run_info(
    *,
    url: Optional[str] = None,
    timeout: float = 10.0,
    json_output: bool = False,
) -> None:
    """Fetch /system_stats and render as table (default) or raw JSON.

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

    # Validate JSON before either code path — catches reverse-proxy HTML 200s.
    try:
        data = response.json()
    except (json.JSONDecodeError, httpx.DecodingError) as exc:
        raise ComfyError(
            "ComfyUI returned a non-JSON response (status 200). "
            "This usually means a reverse proxy is intercepting — check your --url.",
            detail=str(exc),
        ) from exc

    if json_output:
        # Raw byte-for-byte pass-through — consumers pipe to jq or diff.
        sys.stdout.write(response.text)
        sys.stdout.flush()
        return

    _render_table(data)
