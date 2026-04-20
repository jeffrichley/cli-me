"""Logic for `vnccs check all` — nodes + models + server reachability.

Aggregates the three checks into a single pass/fail report. Per
playbook.md §check all, exit code is 0 only if everything is green.
Server reachability uses `backend.get_comfy_url()` + `httpx.get` on
`/system_stats` with a 3-second timeout.
"""

from __future__ import annotations

from typing import Optional

import httpx

from vnccs_cli.backend import get_comfy_url
from vnccs_cli.commands.check_models import run_check_models
from vnccs_cli.commands.check_nodes import run_check_nodes


def _check_server(url: str, *, timeout: float = 3.0) -> dict:
    """Probe ComfyUI's /system_stats endpoint.

    Returns {"url": str, "reachable": bool, "detail": str}. Never raises —
    any exception (connect error, timeout, DNS, etc.) is mapped to
    `reachable=False` with a short detail string for the report.
    """
    try:
        response = httpx.get(f"{url}/system_stats", timeout=timeout)
    except httpx.HTTPError as exc:
        return {
            "url": url,
            "reachable": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "url": url,
            "reachable": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }
    if response.status_code >= 400:
        return {
            "url": url,
            "reachable": False,
            "detail": f"HTTP {response.status_code}",
        }
    return {"url": url, "reachable": True, "detail": f"HTTP {response.status_code}"}


def run_check_all(
    *, comfy_path: Optional[str] = None, comfy_url: Optional[str] = None
) -> dict:
    """Run all three checks and return an aggregated report.

    Returns a dict with:
        - "nodes":  list from run_check_nodes
        - "models": list from run_check_models
        - "server": {"url", "reachable", "detail"}
        - "ok":     bool — True iff all required nodes present, all
                    required (non-optional) models present, and server
                    reachable.

    Raises:
        VnccsPathError: COMFY_PATH unset / not a ComfyUI install (exit 6).
            Propagated unchanged from run_check_nodes / run_check_models.
    """
    nodes_report = run_check_nodes(comfy_path=comfy_path)
    models_report = run_check_models(comfy_path=comfy_path)
    server_report = _check_server(get_comfy_url(comfy_url))

    nodes_ok = all(entry["present"] for entry in nodes_report)
    # Optional models warn-but-don't-fail — only required ones gate exit code.
    models_ok = all(
        entry["present"] for entry in models_report if not entry["optional"]
    )
    server_ok = server_report["reachable"]

    return {
        "nodes": nodes_report,
        "models": models_report,
        "server": server_report,
        "ok": nodes_ok and models_ok and server_ok,
    }
