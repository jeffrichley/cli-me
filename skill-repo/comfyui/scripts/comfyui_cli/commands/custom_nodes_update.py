"""Logic for `comfyui custom-nodes update` — git pull + reinstall requirements."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from comfyui_cli.backend import (
    ComfyError,
    ComfySubprocessError,
    get_comfy_path,
    get_comfy_python,
    run_subprocess,
)

_console = Console()


def _list_git_dirs(custom_nodes: Path) -> list[Path]:
    """Return all custom_nodes/* subdirs that are git repos."""
    return sorted(
        p for p in custom_nodes.iterdir() if p.is_dir() and (p / ".git").exists()
    )


def _update_one(
    node_dir: Path,
    *,
    comfy_python: Optional[Path],
    no_deps: bool,
) -> dict:
    """Run git pull on one custom node dir and optionally reinstall its requirements."""
    pull_result = run_subprocess(
        ["git", "pull", "--ff-only"],
        cwd=node_dir,
        op_name=f"git pull ({node_dir.name})",
    )
    pulled = pull_result.stdout.strip()
    already_up_to_date = "up to date" in pulled.lower() or "up-to-date" in pulled.lower()

    deps_installed = False
    requirements = node_dir / "requirements.txt"
    if requirements.exists() and not no_deps and not already_up_to_date:
        if comfy_python is None:
            _console.print(
                f"[yellow]warning:[/yellow] {node_dir.name} updated but "
                f"no ComfyUI Python interpreter found. Install dependencies "
                f"manually with:\n"
                f"  <your-comfyui-python> -m pip install -r {requirements}"
            )
        else:
            run_subprocess(
                [str(comfy_python), "-m", "pip", "install", "-r", str(requirements)],
                op_name=f"pip install -r requirements.txt ({node_dir.name})",
            )
            deps_installed = True

    return {
        "name": node_dir.name,
        "path": str(node_dir),
        "already_up_to_date": already_up_to_date,
        "deps_installed": deps_installed,
        "git_output": pulled,
    }


def run_update(
    name: Optional[str] = None,
    *,
    all_nodes: bool = False,
    comfy_path: Optional[str] = None,
    python_path: Optional[str] = None,
    no_deps: bool = False,
) -> list[dict]:
    """Update one custom node by name, or all of them with `all_nodes=True`.

    Returns a list of per-node update result dicts.
    """
    if name and all_nodes:
        raise ComfyError("Pass a name OR --all, not both.")
    if not name and not all_nodes:
        raise ComfyError("Pass a custom-node name or --all to update everything.")

    comfy = get_comfy_path(comfy_path)
    custom_nodes = comfy / "custom_nodes"

    if all_nodes:
        targets = _list_git_dirs(custom_nodes)
        if not targets:
            return []
    else:
        target = custom_nodes / name
        if not target.exists():
            raise ComfyError(
                f"Custom node {name!r} is not installed at {target}.",
                detail="Run `comfyui custom-nodes list` to see installed nodes.",
            )
        if not (target / ".git").exists():
            raise ComfyError(
                f"Custom node {name!r} is not a git checkout — cannot update.",
                detail=f"{target} has no .git/ — was it installed manually?",
            )
        targets = [target]

    py = get_comfy_python(comfy, python_path)

    results: list[dict] = []
    for t in targets:
        try:
            results.append(_update_one(t, comfy_python=py, no_deps=no_deps))
        except ComfySubprocessError as e:
            # Continue with the rest in --all mode; record the failure.
            results.append(
                {
                    "name": t.name,
                    "path": str(t),
                    "error": e.message,
                    "detail": e.detail,
                }
            )
            if not all_nodes:
                raise
    return results
