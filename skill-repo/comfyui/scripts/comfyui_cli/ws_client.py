"""WebSocket client for ComfyUI progress events.

See references/techniques/websocket-progress.md for the full event schema and
the `execution_success` vs `executing:{node:null}` terminator quirk.

Used by `queue wait --live` and `workflow run --live`. Renders a per-node
Rich progress bar from `progress` events and terminates on any of:

- `execution_success` for the target prompt_id
- `executing` with `node: null` for the target prompt_id
- `execution_error` for the target prompt_id (exit 4)
- `execution_interrupted` for the target prompt_id (exit 4)
"""

from __future__ import annotations

import json
import uuid
from typing import Callable, Optional
from urllib.parse import urlparse

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)

from comfyui_cli.backend import ComfyConnectionError


_stderr = Console(stderr=True)


def _http_to_ws(base_url: str) -> str:
    """Convert an http(s) base URL to the matching ws(s) scheme."""
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}"


class ComfyWsClient:
    """Minimal WebSocket client for /ws?clientId=... progress streaming."""

    def __init__(
        self, base_url: str, client_id: Optional[str] = None
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id or str(uuid.uuid4())
        self._ws = None  # type: ignore[assignment]

    def connect(self, timeout: float = 120.0) -> None:
        """Open the WebSocket at `<base_url>/ws?clientId=<client_id>`."""
        # Deferred import: websocket-client is a runtime dep but we don't want
        # to force the import when nobody uses --live.
        import websocket  # type: ignore

        ws_base = _http_to_ws(self.base_url)
        url = f"{ws_base}/ws?clientId={self.client_id}"
        ws = websocket.WebSocket()
        ws.connect(url, origin=self.base_url, timeout=timeout)
        ws.settimeout(timeout)
        self._ws = ws

    def watch(
        self,
        *,
        prompt_id: str,
        timeout: float = 600.0,
        on_event: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        """Block until `prompt_id` finishes; return a result dict.

        Result keys:
            status_str: "success" | "error" | "interrupted"
            detail: human-readable detail, or None
        """
        if self._ws is None:
            raise RuntimeError("ComfyWsClient.watch: call connect() first")

        # Deferred import so websocket-client is only required for --live.
        import websocket  # type: ignore

        with Progress(
            TextColumn("[bold]{task.fields[label]}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=_stderr,
            transient=False,
        ) as prog:
            tasks: dict[str, int] = {}
            while True:
                try:
                    frame = self._ws.recv()
                except websocket.WebSocketTimeoutException as exc:
                    raise ComfyConnectionError(
                        "WebSocket receive timed out while waiting for "
                        f"prompt_id={prompt_id}",
                        detail=str(exc),
                    ) from exc
                except websocket.WebSocketException as exc:
                    raise ComfyConnectionError(
                        "WebSocket receive failed",
                        detail=str(exc),
                    ) from exc
                except OSError as exc:
                    raise ComfyConnectionError(
                        "WebSocket connection error",
                        detail=str(exc),
                    ) from exc

                if isinstance(frame, (bytes, bytearray)):
                    # Binary frames (previews) — we don't render them in CLI.
                    continue

                try:
                    msg = json.loads(frame)
                except json.JSONDecodeError:
                    continue

                etype = msg.get("type")
                data = msg.get("data") or {}

                if on_event is not None:
                    try:
                        on_event(msg)
                    except Exception:  # noqa: BLE001
                        pass

                if etype == "executing" and data.get("prompt_id") == prompt_id:
                    node = data.get("node")
                    if node is None:
                        # Primary terminator (main.py:325).
                        return {"status_str": "success", "detail": None}
                    label = f"node {data.get('display_node', node)}"
                    if node not in tasks:
                        tasks[node] = prog.add_task(
                            "", total=1, label=label, completed=0
                        )
                elif etype == "progress" and data.get("prompt_id") == prompt_id:
                    node = data.get("node")
                    value = int(data.get("value") or 0)
                    total = int(data.get("max") or 1)
                    if node not in tasks:
                        tasks[node] = prog.add_task(
                            "", total=total, label=f"node {node}", completed=0
                        )
                    prog.update(tasks[node], total=total, completed=value)
                elif etype == "execution_success" and data.get("prompt_id") == prompt_id:
                    return {"status_str": "success", "detail": None}
                elif etype == "execution_error" and data.get("prompt_id") == prompt_id:
                    msg_text = data.get("exception_message") or ""
                    etype_str = data.get("exception_type") or ""
                    detail = (
                        f"[{etype_str}] {msg_text}" if etype_str else msg_text
                    )
                    return {"status_str": "error", "detail": detail or None}
                elif etype == "execution_interrupted" and data.get("prompt_id") == prompt_id:
                    return {
                        "status_str": "interrupted",
                        "detail": "Execution interrupted",
                    }

    def close(self) -> None:
        """Close the underlying WebSocket."""
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None
