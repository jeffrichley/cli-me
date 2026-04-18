"""server group — probe ComfyUI availability and print system info."""

from typing import Annotated, Optional

import typer

from comfyui_cli import backend
from comfyui_cli.backend import ComfyError
from comfyui_cli.commands import ping as ping_cmd
from comfyui_cli.commands import info as info_cmd

app = typer.Typer(
    help="Probe ComfyUI availability and print system info.",
    no_args_is_help=True,
)


@app.command("ping")
def ping(
    url: Annotated[
        Optional[str],
        typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Request timeout in seconds."),
    ] = 10.0,
) -> None:
    """GET /system_stats; print `ok (...)` on success, exit non-zero on error."""
    try:
        ping_cmd.run_ping(url=url, timeout=timeout)
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("info")
def info(
    url: Annotated[
        Optional[str],
        typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print raw JSON instead of a table."),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Request timeout in seconds."),
    ] = 10.0,
) -> None:
    """Pretty-print /system_stats as a table, or raw JSON with --json."""
    try:
        info_cmd.run_info(url=url, timeout=timeout, json_output=json_output)
    except ComfyError as err:
        backend.print_error_and_exit(err)
