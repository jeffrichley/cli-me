"""queue cancel — POST /queue delete + POST /interrupt (targeted)."""

from __future__ import annotations

from typing import Optional

import httpx
from rich.console import Console

from comfyui_cli.backend import (
    classify_network_error,
    get_base_url,
    handle_http_errors,
    http_client,
)


_console = Console()


def run_cancel(
    *,
    prompt_id: str,
    url: Optional[str] = None,
) -> None:
    """Cancel a specific prompt by id (both pending and running).

    Two-step: POST /queue {"delete": [id]} removes from pending, then
    POST /interrupt {"prompt_id": id} interrupts if it is the running prompt.
    See references/techniques/queue-api.md — POST /interrupt.
    """
    base = get_base_url(url)

    try:
        with http_client(base, timeout=10.0) as client:
            delete_resp = client.post("/queue", json={"delete": [prompt_id]})
            handle_http_errors(delete_resp)

            interrupt_resp = client.post(
                "/interrupt", json={"prompt_id": prompt_id}
            )
            handle_http_errors(interrupt_resp)
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ) as exc:
        raise classify_network_error(exc, base) from exc

    _console.print(f"cancelled {prompt_id}")
