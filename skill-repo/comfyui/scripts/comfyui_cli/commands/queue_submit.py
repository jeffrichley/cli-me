"""queue submit — POST /prompt; print prompt_id on stdout."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Optional

import httpx

from comfyui_cli.backend import (
    ComfyError,
    classify_network_error,
    get_base_url,
    handle_http_errors,
    http_client,
)


def _is_ui_format(data: object) -> bool:
    """Detect UI-format workflow (top-level `nodes` list + `links` list).

    API format is a dict keyed by node id -> {class_type, inputs}; UI format
    has top-level `nodes` and `links` arrays. See
    references/techniques/workflow-formats.md.
    """
    return (
        isinstance(data, dict)
        and isinstance(data.get("nodes"), list)
        and isinstance(data.get("links"), list)
    )


def submit_workflow_dict(
    workflow: dict,
    *,
    url: Optional[str] = None,
    client_id: Optional[str] = None,
    front: bool = False,
) -> dict:
    """POST an already-loaded API-format workflow dict to /prompt.

    Returns a dict with keys: prompt_id, client_id, number, node_errors.
    Raises the same errors as run_submit().
    """
    if _is_ui_format(workflow):
        err = ComfyError(
            "UI-format workflow detected. Export API format "
            "(File \u2192 Export (API Format) with Dev mode enabled). "
            "See references/techniques/workflow-formats.md.",
        )
        err.exit_code = 3
        raise err

    chosen_client_id = client_id or str(uuid.uuid4())

    payload: dict = {
        "prompt": workflow,
        "client_id": chosen_client_id,
    }
    if front:
        payload["front"] = True

    base = get_base_url(url)
    try:
        with http_client(base, timeout=30.0) as client:
            response = client.post("/prompt", json=payload)
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ) as exc:
        raise classify_network_error(exc, base) from exc

    handle_http_errors(response)

    try:
        data = response.json()
    except (json.JSONDecodeError, httpx.DecodingError) as exc:
        raise ComfyError(
            "ComfyUI returned a non-JSON response from /prompt.",
            detail=str(exc),
        ) from exc

    return {
        "prompt_id": data.get("prompt_id"),
        "client_id": chosen_client_id,
        "number": data.get("number"),
        "node_errors": data.get("node_errors") or {},
    }


def run_submit(
    *,
    file: Optional[Path] = None,
    workflow_dict: Optional[dict] = None,
    url: Optional[str] = None,
    client_id: Optional[str] = None,
    front: bool = False,
    json_output: bool = False,
) -> dict:
    """Read a workflow file (or accept a pre-loaded dict), POST to /prompt.

    Exactly one of `file` or `workflow_dict` must be provided. Prints the
    returned prompt_id to stdout (or JSON on --json) and also returns the
    parsed submit result dict so callers composing this step can reuse it.

    Raises:
        ComfyError (exit 3): UI-format workflow detected, or invalid JSON file,
            or file not found.
        ComfyValidationError (exit 3): server returned node_errors.
        ComfyConnectionError (exit 2): server unreachable.
        ComfyError (exit 1): any other non-2xx.
    """
    if (file is None) == (workflow_dict is None):
        raise ComfyError(
            "run_submit: exactly one of `file` or `workflow_dict` is required."
        )

    if workflow_dict is not None:
        workflow = workflow_dict
    else:
        assert file is not None  # for type-checkers
        if not file.exists():
            raise ComfyError(
                f"Workflow file not found: {file}",
                detail=None,
            )

        try:
            raw = file.read_text(encoding="utf-8")
        except OSError as exc:
            raise ComfyError(
                f"Cannot read workflow file: {file}",
                detail=str(exc),
            ) from exc

        try:
            workflow = json.loads(raw)
        except json.JSONDecodeError as exc:
            err = ComfyError(
                f"Workflow file is not valid JSON: {file}",
                detail=str(exc),
            )
            err.exit_code = 3
            raise err from exc

    result = submit_workflow_dict(
        workflow, url=url, client_id=client_id, front=front
    )

    if json_output:
        out = {
            "prompt_id": result["prompt_id"],
            "client_id": result["client_id"],
            "number": result["number"],
            "node_errors": result["node_errors"],
        }
        sys.stdout.write(json.dumps(out))
        sys.stdout.flush()
        return result

    # Plain stdout: stdout-friendly, machine-parseable two-line form.
    sys.stdout.write(f"prompt_id={result['prompt_id']}\n")
    sys.stdout.write(f"client_id={result['client_id']}\n")
    sys.stdout.flush()
    return result
