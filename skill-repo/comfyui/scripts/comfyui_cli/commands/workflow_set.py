"""workflow set — parameter substitution (NODE_ID.key, @Title.key, class:Class.key).

Per references/techniques/workflow-params.md:

- `NODE_ID.input_key=VALUE` — lsplit once on `.` (node ids can't contain `.`)
- `@Title.input_key=VALUE` — rsplit once on `.`; matches `_meta.title` exactly,
  falls back to `class_type` when no node has that title. Ambiguity is an error.
- `class:ClassName.input_key=VALUE` — rsplit once on `.`; matches `class_type`
  exactly. Ambiguity is an error.
- Values parse as JSON first, fall back to raw string.
- `seed=random` → uniform `[0, 2**32)`; `seed=random64` → uniform `[0, 2**63)`.
  Resolved BEFORE JSON parsing and printed to stderr for reproducibility.
"""

from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path
from typing import Any, List, Optional

from rich.console import Console

from comfyui_cli.backend import ComfyError


_stderr = Console(stderr=True)


def _parse_param(param: str) -> tuple[str, str]:
    """Split a single `--param` string into (key, value) on the first `=`.

    Raises ComfyError if no `=` appears.
    """
    if "=" not in param:
        raise ComfyError(
            f"Bad --param {param!r}: expected KEY=VALUE (no '=' found).",
        )
    key, _, value = param.partition("=")
    return key, value


def _parse_value(raw: str) -> Any:
    """JSON-parse raw value, falling back to the literal string."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _resolve_seed_token(value: str) -> Optional[int]:
    """Resolve `random` / `random64` to a concrete int. None otherwise."""
    if value == "random":
        # secrets is cryptographically random; plenty of entropy for seeds
        return secrets.randbelow(2**32)
    if value == "random64":
        return secrets.randbelow(2**63)
    return None


def _resolve_target(workflow: dict, key: str) -> tuple[str, str]:
    """Return (node_id, input_key) for a KEY spec.

    Raises ComfyError for ambiguity or missing nodes.
    """
    if key.startswith("@"):
        # @Title.input_key — rsplit so title can contain '.'
        title_plus_key = key[1:]
        if "." not in title_plus_key:
            raise ComfyError(
                f"Bad --param key {key!r}: expected @Title.input_key",
            )
        title, input_key = title_plus_key.rsplit(".", 1)
        matches_by_title = [
            nid
            for nid, node in workflow.items()
            if isinstance(node, dict)
            and node.get("_meta", {}).get("title") == title
        ]
        if len(matches_by_title) > 1:
            raise ComfyError(
                _ambiguous_msg(
                    kind=f"title {title!r}",
                    matches=matches_by_title,
                    workflow=workflow,
                )
            )
        if len(matches_by_title) == 1:
            return matches_by_title[0], input_key
        # Fallback: match by class_type (when no _meta.title matches)
        matches_by_class = [
            nid
            for nid, node in workflow.items()
            if isinstance(node, dict) and node.get("class_type") == title
        ]
        if len(matches_by_class) > 1:
            raise ComfyError(
                _ambiguous_msg(
                    kind=f"title {title!r} (fallback to class_type)",
                    matches=matches_by_class,
                    workflow=workflow,
                )
            )
        if len(matches_by_class) == 1:
            return matches_by_class[0], input_key
        raise ComfyError(
            f"No node with title or class_type {title!r}.",
        )
    if key.startswith("class:"):
        # class:ClassName.input_key — rsplit so class names never collide with key
        rest = key[len("class:") :]
        if "." not in rest:
            raise ComfyError(
                f"Bad --param key {key!r}: expected class:CLASS.input_key",
            )
        class_name, input_key = rest.rsplit(".", 1)
        matches = [
            nid
            for nid, node in workflow.items()
            if isinstance(node, dict) and node.get("class_type") == class_name
        ]
        if len(matches) > 1:
            raise ComfyError(
                _ambiguous_msg(
                    kind=f"class_type {class_name!r}",
                    matches=matches,
                    workflow=workflow,
                )
            )
        if len(matches) == 0:
            raise ComfyError(
                f"No node with class_type {class_name!r}.",
            )
        return matches[0], input_key
    # NODE_ID.input_key — lsplit (node ids can't contain '.')
    if "." not in key:
        raise ComfyError(
            f"Bad --param key {key!r}: expected NODE_ID.input_key",
        )
    node_id, input_key = key.split(".", 1)
    if node_id not in workflow:
        raise ComfyError(
            f"No node with id {node_id!r} in workflow.",
        )
    return node_id, input_key


def _ambiguous_msg(*, kind: str, matches: list[str], workflow: dict) -> str:
    """Format an ambiguity error per workflow-params.md R1 fix."""
    lines = [
        f"Ambiguous --param: {len(matches)} nodes match {kind}. "
        "Use NODE_ID.key addressing instead.",
    ]
    for nid in matches:
        node = workflow.get(nid, {})
        title = (node.get("_meta") or {}).get("title")
        class_type = node.get("class_type", "?")
        suffix = f" title={title!r}" if title else ""
        lines.append(f"  - node {nid}: class_type={class_type}{suffix}")
    return "\n".join(lines)


def _apply_param(workflow: dict, param: str) -> None:
    """Apply a single `KEY=VALUE` to `workflow` in place."""
    key, raw_value = _parse_param(param)
    node_id, input_key = _resolve_target(workflow, key)

    # Seed token resolution happens BEFORE JSON parse — see workflow-params.md.
    seed_int = _resolve_seed_token(raw_value)
    if seed_int is not None:
        value: Any = seed_int
        _stderr.print(
            f"[dim]resolved {key}={raw_value} -> {seed_int}[/dim]"
        )
    else:
        value = _parse_value(raw_value)

    node = workflow[node_id]
    node.setdefault("inputs", {})[input_key] = value


def run_set(
    *,
    in_file: Path,
    params: List[str],
    out_file: Optional[Path],
    inline: bool,
) -> None:
    """Apply `--param` substitutions; write to out_file, stdout, or in place."""
    if inline and out_file is not None:
        raise ComfyError("--inline and -o/--output are mutually exclusive.")

    try:
        workflow = json.loads(in_file.read_text())
    except FileNotFoundError as exc:
        raise ComfyError(f"Workflow file not found: {in_file}") from exc
    except json.JSONDecodeError as exc:
        raise ComfyError(
            f"Workflow file is not valid JSON: {in_file}",
            detail=str(exc),
        ) from exc

    if not isinstance(workflow, dict):
        raise ComfyError(
            "Workflow JSON must be an object (API format).",
        )

    for p in params:
        _apply_param(workflow, p)

    rendered = json.dumps(workflow, indent=2) + "\n"

    if inline:
        in_file.write_text(rendered)
    elif out_file is not None:
        out_file.write_text(rendered)
    else:
        sys.stdout.write(rendered)
        sys.stdout.flush()


# Backwards-compatibility alias — workflow.py currently imports
# `run_workflow_set`. Keep both names live during the transition.
def run_workflow_set(
    *,
    file: Path,
    params: List[str],
    output: Optional[Path] = None,
    inline: bool = False,
) -> None:
    run_set(in_file=file, params=params, out_file=output, inline=inline)
