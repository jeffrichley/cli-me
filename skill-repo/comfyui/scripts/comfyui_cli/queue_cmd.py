"""queue group — submit prompts, track status, cancel/clear, free memory.

Named `queue_cmd` to avoid shadowing the stdlib `queue` module.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from comfyui_cli import backend
from comfyui_cli.backend import ComfyError
from comfyui_cli.commands import queue_cancel
from comfyui_cli.commands import queue_clear
from comfyui_cli.commands import queue_free
from comfyui_cli.commands import queue_list as queue_list_cmd
from comfyui_cli.commands import queue_status
from comfyui_cli.commands import queue_submit
from comfyui_cli.commands import queue_wait

app = typer.Typer(
    help="Submit prompts, track status, cancel/clear the queue, free memory.",
    no_args_is_help=True,
)


_UrlOpt = Annotated[
    Optional[str],
    typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
]

_JsonOpt = Annotated[
    bool,
    typer.Option("--json", help="Emit raw JSON instead of a table."),
]


@app.command("submit")
def submit(
    file: Annotated[Path, typer.Argument(help="Workflow JSON file (API format).")],
    client_id: Annotated[
        Optional[str],
        typer.Option(
            "--client-id",
            help="Stable client_id so /ws events reach this client.",
        ),
    ] = None,
    front: Annotated[
        bool,
        typer.Option("--front", help="Enqueue ahead of existing pending items."),
    ] = False,
    url: _UrlOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """POST /prompt; print prompt_id on stdout."""
    try:
        queue_submit.run_submit(
            file=file,
            client_id=client_id,
            front=front,
            url=url,
            json_output=json_output,
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("status")
def status(
    prompt_id: Annotated[
        Optional[str],
        typer.Argument(help="Prompt ID to check; omit to list the queue."),
    ] = None,
    url: _UrlOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Show status for a prompt via /history, or overall queue via /queue."""
    try:
        queue_status.run_status(
            prompt_id=prompt_id, url=url, json_output=json_output
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("list")
def list_cmd(
    url: _UrlOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """GET /queue and render a human-readable table."""
    try:
        queue_list_cmd.run_list(url=url, json_output=json_output)
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("wait")
def wait(
    prompt_id: Annotated[str, typer.Argument(help="Prompt ID to wait on.")],
    live: Annotated[
        bool,
        typer.Option(
            "--live",
            help="Stream /ws progress events instead of polling /history.",
        ),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Overall timeout in seconds."),
    ] = 600.0,
    client_id: Annotated[
        Optional[str],
        typer.Option(
            "--client-id",
            help="Client ID to use on /ws (must match --live submission).",
        ),
    ] = None,
    url: _UrlOpt = None,
) -> None:
    """Poll /history until prompt finishes, or stream /ws if --live."""
    try:
        queue_wait.run_wait(
            prompt_id=prompt_id,
            live=live,
            timeout=timeout,
            client_id=client_id,
            url=url,
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("cancel")
def cancel(
    prompt_id: Annotated[str, typer.Argument(help="Prompt ID to cancel.")],
    url: _UrlOpt = None,
) -> None:
    """POST /queue delete + POST /interrupt to cancel a specific prompt."""
    try:
        queue_cancel.run_cancel(prompt_id=prompt_id, url=url)
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("clear")
def clear(
    url: _UrlOpt = None,
) -> None:
    """POST /queue with {"clear": true} to drop everything pending."""
    try:
        queue_clear.run_clear(url=url)
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("free")
def free(
    unload_models: Annotated[
        bool,
        typer.Option("--unload-models", help="Unload models from VRAM."),
    ] = False,
    free_memory: Annotated[
        bool,
        typer.Option("--free-memory", help="Free cached memory."),
    ] = False,
    url: _UrlOpt = None,
) -> None:
    """POST /free to reclaim VRAM / system memory."""
    try:
        queue_free.run_free(
            unload_models=unload_models, free_memory=free_memory, url=url
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)
