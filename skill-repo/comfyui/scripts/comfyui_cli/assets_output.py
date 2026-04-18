"""output group — download and inspect workflow outputs.

Named `assets_output` because `output` collides with `input` stylistically.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from comfyui_cli import backend
from comfyui_cli.backend import ComfyError
from comfyui_cli.commands import output_download as output_download_cmd
from comfyui_cli.commands import output_show as output_show_cmd

app = typer.Typer(
    help="Download and inspect outputs for a given prompt_id.",
    no_args_is_help=True,
)


_UrlOpt = Annotated[
    Optional[str],
    typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
]
_JsonOpt = Annotated[
    bool,
    typer.Option("--json", help="Emit JSON summary instead of a table."),
]


@app.command("download")
def download(
    prompt_id: Annotated[
        str, typer.Argument(help="Prompt ID to download outputs for.")
    ],
    dir: Annotated[
        Optional[Path],
        typer.Option(
            "--dir",
            help="Destination directory (default: ./comfy_outputs).",
        ),
    ] = None,
    url: _UrlOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Resolve /history for the prompt_id, then GET /view for each output image."""
    try:
        output_download_cmd.run_download(
            prompt_id=prompt_id,
            dest_dir=dir,
            url=url,
            json_output=json_output,
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("show")
def show(
    prompt_id: Annotated[str, typer.Argument(help="Prompt ID to inspect.")],
    url: _UrlOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Print the outputs section from /history/<prompt_id> as JSON."""
    try:
        output_show_cmd.run_show(
            prompt_id=prompt_id,
            url=url,
            json_output=json_output,
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)
