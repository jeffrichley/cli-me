"""Shared backend utilities for ComfyUI CLI.

- URL resolution (flag > env > default)
- httpx client factory with origin-guard header set
- Typed exception hierarchy and HTTP error handling
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
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


class ComfyPathError(ComfyError):
    """ComfyUI install path is not set, missing, or doesn't look like a ComfyUI install."""

    exit_code = 6


class ComfySubprocessError(ComfyError):
    """git or pip subprocess failed; stderr is surfaced in `detail`."""

    exit_code = 7


# --- URL / client helpers --------------------------------------------------


def get_base_url(cli_url: Optional[str] = None) -> str:
    """Resolve the ComfyUI base URL.

    Precedence: --url flag > COMFY_URL env > default (127.0.0.1:8188).
    Trailing slashes are stripped.
    """
    url = cli_url or os.environ.get("COMFY_URL") or DEFAULT_BASE_URL
    return url.rstrip("/")


def get_comfy_path(cli_path: Optional[str] = None) -> Path:
    """Resolve the ComfyUI install directory.

    Precedence: --path flag > COMFY_PATH env > error. Validates the path
    exists and contains a `custom_nodes/` subdirectory (the canonical
    marker that this is a ComfyUI install root).

    Raises:
        ComfyPathError: when the path is unset, missing, or doesn't have
            a custom_nodes/ subdir.
    """
    raw = cli_path or os.environ.get("COMFY_PATH")
    if not raw:
        raise ComfyPathError(
            "ComfyUI install path not set.",
            detail=(
                "Pass --path /path/to/ComfyUI, or set the COMFY_PATH env var.\n"
                "This should be the directory that contains custom_nodes/, models/, etc."
            ),
        )
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise ComfyPathError(
            f"ComfyUI path does not exist: {path}",
            detail=f"Resolved from {'--path' if cli_path else 'COMFY_PATH'}={raw!r}.",
        )
    custom_nodes_dir = path / "custom_nodes"
    if not custom_nodes_dir.is_dir():
        raise ComfyPathError(
            f"Path is not a ComfyUI install: {path}",
            detail=(
                f"Expected '{custom_nodes_dir}' to be a directory.\n"
                "Point --path or COMFY_PATH at the directory that contains main.py "
                "and custom_nodes/."
            ),
        )
    return path


def _candidate_pythons(comfy_path: Path) -> list[Path]:
    """Return likely Python interpreter paths for ComfyUI's environment, in priority order."""
    candidates = []
    if sys.platform == "win32":
        candidates += [
            comfy_path / "python_embeded" / "python.exe",  # portable Windows install
            comfy_path / ".venv" / "Scripts" / "python.exe",
            comfy_path / "venv" / "Scripts" / "python.exe",
        ]
    else:
        candidates += [
            comfy_path / ".venv" / "bin" / "python",
            comfy_path / "venv" / "bin" / "python",
        ]
    return candidates


def get_comfy_python(
    comfy_path: Path, cli_python: Optional[str] = None
) -> Optional[Path]:
    """Resolve the Python interpreter that runs ComfyUI.

    Used to `pip install -r requirements.txt` for newly-installed custom
    nodes into the right environment. Custom nodes loaded by ComfyUI must
    have their requirements installed in ComfyUI's own Python.

    Precedence: --python flag > COMFY_PYTHON env > auto-detect candidates
    next to comfy_path. Returns None if nothing is found — callers should
    skip pip install and warn the user with a clear instruction.
    """
    raw = cli_python or os.environ.get("COMFY_PYTHON")
    if raw:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            raise ComfyPathError(
                f"Specified Python interpreter does not exist: {path}",
                detail=f"Resolved from {'--python' if cli_python else 'COMFY_PYTHON'}={raw!r}.",
            )
        return path
    for cand in _candidate_pythons(comfy_path):
        if cand.exists():
            return cand
    return None


def run_subprocess(
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    timeout: float = 600.0,
    op_name: str = "subprocess",
) -> subprocess.CompletedProcess:
    """Run a subprocess and translate failures into ComfySubprocessError.

    On non-zero exit, raises ComfySubprocessError with stderr surfaced in
    `detail`. This is the equivalent of the pandoc backend's run_pandoc
    pattern — wrapped tools' stderr must reach the user instead of a
    Python traceback.
    """
    if not cmd or not cmd[0]:
        raise ComfySubprocessError(f"{op_name}: empty command", detail=str(cmd))
    exe = shutil.which(cmd[0]) or cmd[0]
    full_cmd = [exe] + cmd[1:]
    try:
        result = subprocess.run(
            full_cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as e:
        raise ComfySubprocessError(
            f"{op_name}: command not found: {cmd[0]}",
            detail=str(e),
        ) from e
    except subprocess.TimeoutExpired as e:
        raise ComfySubprocessError(
            f"{op_name}: timed out after {timeout}s",
            detail=str(e),
        ) from e
    if result.returncode != 0:
        raise ComfySubprocessError(
            f"{op_name} failed (exit {result.returncode})",
            detail=(result.stderr or result.stdout or "").strip(),
        )
    return result


def _rmtree_handle_readonly(func, path, exc_info):
    """shutil.rmtree onerror callback that flips the read-only bit and retries.

    Git stores files in `.git/objects/` as read-only; on Windows shutil.rmtree
    fails on those without this handler. Cross-platform safe — chmod 0o700 is
    a no-op on POSIX where the parent dir owner can already remove children.
    """
    import os
    import stat as _stat

    try:
        os.chmod(path, _stat.S_IWRITE | _stat.S_IREAD)
        func(path)
    except Exception:
        # Re-raise the original error to the caller; we tried.
        raise


def safe_rmtree(path: Path) -> None:
    """Recursive delete that handles Windows read-only files (e.g. .git/)."""
    if not path.exists():
        return
    shutil.rmtree(str(path), onerror=_rmtree_handle_readonly)


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
