"""workflow validate — client-side structural checks on API-format JSON.

Detects UI format (`"nodes"` + `"links"` top-level) and emits re-export
instructions (exit 3). Validates:

- Each value has a non-empty `class_type` string.
- Each value has an `inputs` dict.
- Each `[src_id, slot]` link references a node id that exists in the workflow.
- Warns (not errors) on duplicate `_meta.title` values.

Reports all issues, then either prints "ok" (exit 0) or raises
ComfyValidationError (exit 3).
"""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from comfyui_cli.backend import ComfyError, ComfyValidationError


_console = Console()
_stderr = Console(stderr=True)


_UI_REEXPORT_MSG = (
    "This looks like a UI-format workflow (it has top-level 'nodes' and "
    "'links' arrays). The /prompt endpoint only accepts API format.\n"
    "To get an API-format workflow:\n"
    "  1. Open the ComfyUI web UI\n"
    "  2. Settings -> enable 'Enable Dev mode Options'\n"
    "  3. Workflow menu -> 'Export (API Format)'\n"
    "Or extract the API workflow from a generated image:\n"
    "  comfyui workflow extract path/to/image.png"
)


def _is_ui_format(data: dict) -> bool:
    return (
        "nodes" in data
        and isinstance(data.get("nodes"), list)
        and "links" in data
    )


def _check_links(workflow: dict, issues: list[str]) -> None:
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue
        for input_key, value in inputs.items():
            # A link is a 2-element list [src_id, slot]
            if (
                isinstance(value, list)
                and len(value) == 2
                and isinstance(value[0], str)
                and isinstance(value[1], int)
            ):
                src_id = value[0]
                if src_id not in workflow:
                    issues.append(
                        f"node {node_id!r} input {input_key!r} references "
                        f"missing node id {src_id!r}"
                    )


def _check_title_duplicates(workflow: dict, warnings: list[str]) -> None:
    titles: dict[str, list[str]] = {}
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        title = (node.get("_meta") or {}).get("title")
        if not isinstance(title, str):
            continue
        titles.setdefault(title, []).append(node_id)
    for title, ids in titles.items():
        if len(ids) > 1:
            warnings.append(
                f"duplicate _meta.title {title!r} on nodes {ids} — "
                "@Title addressing will error; use NODE_ID.key"
            )


def run_validate(*, file: Path) -> None:
    """Validate a workflow JSON file; print 'ok' or raise ComfyValidationError."""
    try:
        data = json.loads(file.read_text())
    except FileNotFoundError as exc:
        raise ComfyError(f"Workflow file not found: {file}") from exc
    except json.JSONDecodeError as exc:
        raise ComfyValidationError(
            f"Workflow file is not valid JSON: {file}",
            detail=str(exc),
        ) from exc

    if not isinstance(data, dict):
        raise ComfyValidationError(
            "Workflow JSON must be an object (API format).",
        )

    if _is_ui_format(data):
        raise ComfyValidationError(_UI_REEXPORT_MSG)

    issues: list[str] = []
    warnings: list[str] = []

    for node_id, node in data.items():
        if not isinstance(node, dict):
            issues.append(f"node {node_id!r} is not an object")
            continue
        class_type = node.get("class_type")
        if not isinstance(class_type, str) or not class_type:
            issues.append(
                f"node {node_id!r} is missing a non-empty 'class_type' string"
            )
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            issues.append(f"node {node_id!r} is missing an 'inputs' dict")

    _check_links(data, issues)
    _check_title_duplicates(data, warnings)

    for w in warnings:
        _stderr.print(f"[yellow]warning:[/yellow] {w}")

    if issues:
        lines = ["Workflow has validation errors:"]
        lines.extend(f"  - {i}" for i in issues)
        raise ComfyValidationError("\n".join(lines))

    _console.print("ok")


# Backwards-compatibility alias
def run_workflow_validate(*, file: Path) -> None:
    run_validate(file=file)
