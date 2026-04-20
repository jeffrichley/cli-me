"""Logic for `comfyui custom-nodes install` — git clone a custom node pack into ComfyUI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from rich.console import Console

from comfyui_cli import backend
from comfyui_cli.backend import (
    ComfyError,
    ComfyPathError,
    ComfySubprocessError,
    get_comfy_path,
    get_comfy_python,
    run_subprocess,
    safe_rmtree,
)

_console = Console()


def derive_name(repo_url: str) -> str:
    """Derive the install directory name from a git URL.

    Strips trailing `.git`, takes the last path segment.
        https://github.com/AHEKOT/ComfyUI_VNCCS.git -> ComfyUI_VNCCS
        git@github.com:foo/bar.git                  -> bar
    """
    raw = repo_url.strip().rstrip("/")
    if raw.endswith(".git"):
        raw = raw[:-4]
    # SSH form: git@host:path
    if ":" in raw and not raw.startswith(("http://", "https://", "ssh://")):
        raw = raw.split(":", 1)[-1]
    parsed = urlparse(raw)
    path = parsed.path or raw
    segments = [s for s in path.split("/") if s]
    if not segments:
        raise ValueError(f"Cannot derive a name from {repo_url!r}")
    return segments[-1]


def run_install(
    repo_url: str,
    *,
    name: Optional[str] = None,
    comfy_path: Optional[str] = None,
    python_path: Optional[str] = None,
    no_deps: bool = False,
    force: bool = False,
) -> dict:
    """Clone a custom node repo into ComfyUI/custom_nodes/ and optionally install requirements.

    Returns a dict summarizing the install:
        {"name": ..., "path": ..., "deps_installed": bool, "restart_required": True}

    Behavior:
        - Idempotent by default: existing `<custom_nodes>/<name>` triggers
          a no-op return with a note (unless `force=True`, which deletes
          and re-clones).
        - If the repo has `requirements.txt` and `no_deps` is False, runs
          `<comfy_python> -m pip install -r requirements.txt`. Skips with a
          warning when no Python interpreter can be located.
        - Always notes that ComfyUI must be restarted for the node to load
          (ComfyUI does not hot-reload custom nodes).
    """
    install_name = name or derive_name(repo_url)
    if not install_name or install_name in (".", ".."):
        raise ComfyError(
            f"Refusing to install with name {install_name!r} — pick something safer with --name."
        )

    comfy = get_comfy_path(comfy_path)
    custom_nodes = comfy / "custom_nodes"
    target = custom_nodes / install_name

    if target.exists():
        if not force:
            return {
                "name": install_name,
                "path": str(target),
                "deps_installed": False,
                "skipped": True,
                "reason": "already installed (pass --force to re-clone)",
                "restart_required": False,
            }
        _rmtree(target)

    # git clone
    run_subprocess(
        ["git", "clone", "--depth", "1", repo_url, str(target)],
        op_name="git clone",
    )

    deps_installed = False
    requirements = target / "requirements.txt"
    if requirements.exists() and not no_deps:
        py = get_comfy_python(comfy, python_path)
        if py is None:
            _console.print(
                f"[yellow]warning:[/yellow] {requirements.name} present but "
                "no ComfyUI Python interpreter found. Install dependencies "
                "manually with:\n"
                f"  <your-comfyui-python> -m pip install -r {requirements}\n"
                "Or pass --python /path/to/comfyui/python next time."
            )
        else:
            run_subprocess(
                [str(py), "-m", "pip", "install", "-r", str(requirements)],
                op_name="pip install -r requirements.txt",
            )
            deps_installed = True

    return {
        "name": install_name,
        "path": str(target),
        "deps_installed": deps_installed,
        "skipped": False,
        "restart_required": True,
    }


def _rmtree(path: Path) -> None:
    """Best-effort recursive delete; raise as ComfyError on permission issues.

    Uses backend.safe_rmtree which handles read-only files (notably git's
    object store on Windows).
    """
    try:
        safe_rmtree(path)
    except OSError as e:
        raise ComfyError(
            f"Could not remove existing directory {path}",
            detail=str(e),
        ) from e
