"""workflow run — submit + wait + download outputs; auto-detects JSON/PNG/WebP.

Compositional command that wires together:
  * queue_submit.submit_workflow_dict (in-process; no disk roundtrip)
  * queue_wait.run_wait (live /ws streaming or polling /history)
  * output_download.run_download (save /view bytes to disk)

On success emits a Rich summary table (or JSON with --json) describing the
prompt_id and downloaded output files. Errors surface via the standard
ComfyError hierarchy with exit codes matching the underlying commands.
"""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from comfyui_cli.backend import ComfyError, ComfyNotFoundError
from comfyui_cli.commands import output_download as _output_download
from comfyui_cli.commands import queue_submit as _queue_submit
from comfyui_cli.commands import queue_wait as _queue_wait
from comfyui_cli.commands import workflow_extract as _workflow_extract


_console = Console()
_stderr = Console(stderr=True)


_IMAGE_SUFFIXES = {".png", ".webp"}


def _load_api_workflow(file: Path) -> dict:
    """Materialize an API-format workflow from a .json, .png, or .webp file.

    - .json: parsed and rejected (exit 3) if it is UI-format.
    - .png/.webp: extracts the embedded `prompt` chunk. Missing chunk = exit 5.
    """
    if not file.exists():
        raise ComfyError(f"Workflow file not found: {file}")

    suffix = file.suffix.lower()
    if suffix in _IMAGE_SUFFIXES:
        # Pure extraction — raises ComfyNotFoundError (exit 5) on missing.
        return _workflow_extract.extract_api_dict(file)

    # Default path: parse as JSON. UI-format rejection happens inside
    # submit_workflow_dict via _is_ui_format, so we don't duplicate it here.
    try:
        raw = file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ComfyError(
            f"Cannot read workflow file: {file}", detail=str(exc)
        ) from exc

    try:
        data = _json.loads(raw)
    except _json.JSONDecodeError as exc:
        err = ComfyError(
            f"Workflow file is not valid JSON: {file}", detail=str(exc)
        )
        err.exit_code = 3
        raise err from exc

    if not isinstance(data, dict):
        err = ComfyError(
            f"Workflow file is not an object: {file}",
            detail="Expected API-format workflow (dict keyed by node id).",
        )
        err.exit_code = 3
        raise err

    return data


def _print_summary(
    prompt_id: str,
    saved: list,
    skipped: list,
    *,
    json_output: bool,
) -> None:
    """Render the final workflow-run result."""
    if json_output:
        out = {
            "prompt_id": prompt_id,
            "status": "success",
            "outputs": [
                {"path": item["path"], "bytes": item["size"]} for item in saved
            ],
            "skipped": skipped,
        }
        sys.stdout.write(_json.dumps(out))
        sys.stdout.write("\n")
        sys.stdout.flush()
        return

    table = Table(title=f"workflow run \u2714 {prompt_id}", title_style="bold green")
    table.add_column("Output path")
    table.add_column("Bytes", justify="right")
    for item in saved:
        table.add_row(item["path"], f"{item['size']:,}")
    if not saved:
        table.add_row("(no outputs)", "-")
    _console.print(table)
    if skipped:
        _console.print(f"[yellow]skipped {len(skipped)} files[/yellow]")


def _download_outputs_dict(
    *,
    prompt_id: str,
    dest_dir: Optional[Path],
    url: Optional[str],
) -> tuple[list, list]:
    """Drive output_download directly; return (saved, skipped) lists.

    We ask output_download to emit JSON to stdout, capture it, then return
    the parsed lists. This avoids re-implementing the /history + /view logic
    while still letting `workflow run` render a unified summary.
    """
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _output_download.run_download(
            prompt_id=prompt_id,
            dest_dir=dest_dir,
            url=url,
            json_output=True,
        )
    text = buf.getvalue().strip()
    if not text:
        return [], []
    try:
        parsed = _json.loads(text)
    except _json.JSONDecodeError as exc:
        raise ComfyError(
            "Could not parse output_download JSON while composing workflow run.",
            detail=str(exc),
        ) from exc
    return parsed.get("saved", []) or [], parsed.get("skipped", []) or []


def run_run(
    *,
    file: Path,
    url: Optional[str] = None,
    live: bool = True,
    output_dir: Optional[Path] = None,
    client_id: Optional[str] = None,
    front: bool = False,
    timeout: float = 600.0,
    json_output: bool = False,
) -> None:
    """End-to-end: submit, wait, download. Accepts .json, .png, or .webp.

    Exit codes follow the individual commands:
        3  UI-format / invalid JSON / node_errors
        5  image has no embedded workflow / prompt_id missing in /history
        2  server unreachable
        4  execution error on the prompt
        1  timeout / generic
    """
    api_workflow = _load_api_workflow(file)

    # 1. Submit (in-process; no tempfile).
    submit_result = _queue_submit.submit_workflow_dict(
        api_workflow, url=url, client_id=client_id, front=front
    )
    prompt_id = submit_result["prompt_id"]
    chosen_client_id = submit_result["client_id"]
    if not prompt_id:
        raise ComfyError(
            "ComfyUI /prompt response did not include a prompt_id.",
            detail=str(submit_result),
        )

    _stderr.print(f"[dim]submitted prompt_id={prompt_id}[/dim]")

    # 2. Wait for completion. run_wait raises ComfyExecutionError (exit 4)
    #    on failure, ComfyError (exit 1) on timeout — no extra branching here.
    _queue_wait.run_wait(
        prompt_id=prompt_id,
        url=url,
        timeout=timeout,
        live=live,
        client_id=chosen_client_id,
    )

    # 3. Download outputs.
    saved, skipped = _download_outputs_dict(
        prompt_id=prompt_id, dest_dir=output_dir, url=url
    )

    # 4. Summary.
    _print_summary(prompt_id, saved, skipped, json_output=json_output)


# Backwards-compatibility alias for the old stub name.
def run_workflow_run(
    *,
    file: Path,
    live: bool = False,
    output_dir: Optional[Path] = None,
    url: Optional[str] = None,
) -> None:
    run_run(file=file, live=live, output_dir=output_dir, url=url)
