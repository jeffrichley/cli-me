"""input group — upload and list input images.

Named `assets_input` because `input` is a Python builtin.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from comfyui_cli import backend
from comfyui_cli.backend import ComfyError
from comfyui_cli.commands import input_list as input_list_cmd
from comfyui_cli.commands import input_upload as input_upload_cmd

app = typer.Typer(
    help="Upload and list input images on the ComfyUI server.",
    no_args_is_help=True,
)


_UrlOpt = Annotated[
    Optional[str],
    typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
]
_JsonOpt = Annotated[
    bool,
    typer.Option("--json", help="Emit JSON (pretty-printed for upload)."),
]


@app.command("upload")
def upload(
    file: Annotated[Path, typer.Argument(help="Image file to upload.")],
    subfolder: Annotated[
        Optional[str],
        typer.Option("--subfolder", help="Target subfolder under /input."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Overwrite if a file with the same name exists.",
        ),
    ] = False,
    url: _UrlOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """POST /upload/image; prints {"name", "subfolder", "type"} on success.

    The server may rename on collision (when --overwrite is not set). Always
    use the returned `name` field, never the local filename.
    """
    try:
        input_upload_cmd.run_upload(
            file=file,
            subfolder=subfolder,
            overwrite=overwrite,
            url=url,
            json_output=json_output,
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("list")
def list_cmd(
    subfolder: Annotated[
        Optional[str],
        typer.Option("--subfolder", help="Subfolder under /input to list."),
    ] = None,
    local: Annotated[
        bool,
        typer.Option(
            "--local",
            help=(
                "Required: ComfyUI has no input-listing endpoint; lists the "
                "local filesystem under $COMFY_ROOT/input (default "
                "E:\\workspaces\\tools\\comfy\\ComfyUI)."
            ),
        ),
    ] = False,
    url: _UrlOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """List input images — requires --local (server exposes no listing endpoint)."""
    try:
        input_list_cmd.run_list(
            subfolder=subfolder,
            local=local,
            url=url,
            json_output=json_output,
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)
