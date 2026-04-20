"""Assertion helpers for comfyui-vnccs QA tests.

Importable as ``from _vnccs_helpers import ...``. Lives outside conftest
because conftest is auto-loaded by pytest, not meant to be imported by
name (importlib mode breaks ``from conftest import ...``). Skill-prefixed
so it doesn't collide with other skills' helpers when the whole-suite runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def assert_workflow_sha256(path: Path, expected: str) -> None:
    """Assert a bundled workflow JSON matches its pinned SHA-256.

    Catches accidental modifications to bundled workflows (they should be
    byte-identical to the pinned upstream commit). See
    scripts/workflows/README.md for the expected hashes.
    """
    assert path.exists(), f"Bundled workflow missing: {path}"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, (
        f"Workflow {path.name} has sha256 {actual}; expected {expected}. "
        "Bundled workflows should be byte-identical to the pinned upstream "
        "commit. Has the file been modified locally?"
    )


def assert_valid_json(path: Path) -> dict:
    """Assert a file contains parseable JSON and return the parsed dict."""
    assert path.exists(), f"File missing: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise AssertionError(f"Not valid JSON: {path} — {e}") from e


def assert_workflow_has_class_type(workflow: dict, class_type: str) -> None:
    """Assert a class_type string appears somewhere in a workflow JSON tree.

    Walks the workflow dict (including nested subgraphs in GUI-format
    workflows) looking for any node with the given class_type.
    """
    found = []

    def walk(x):
        if isinstance(x, dict):
            for k in ("class_type", "type"):
                v = x.get(k)
                if isinstance(v, str) and v == class_type:
                    found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(workflow)
    assert found, (
        f"No node with class_type={class_type!r} found in workflow. "
        f"(Searched entire tree including subgraphs.)"
    )
