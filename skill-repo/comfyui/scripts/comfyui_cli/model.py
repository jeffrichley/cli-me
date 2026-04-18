"""model group — list and find model files on the ComfyUI server."""

from typing import Annotated, Optional

import typer

from comfyui_cli import backend
from comfyui_cli.backend import ComfyError
from comfyui_cli.commands import model_find, model_list

app = typer.Typer(
    help="List and find model files (checkpoints, loras, vae, etc.).",
    no_args_is_help=True,
)


_UrlOpt = Annotated[
    Optional[str],
    typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
]

_JsonOpt = Annotated[
    bool,
    typer.Option("--json", help="Emit JSON instead of a Rich table."),
]


@app.command("list")
def list_cmd(
    type: Annotated[
        Optional[str],
        typer.Option(
            "--type",
            help=(
                "Model type: checkpoints, loras, vae, controlnet, "
                "upscale_models, text_encoders, embeddings. "
                "See references/techniques/models-and-assets.md."
            ),
        ),
    ] = None,
    url: _UrlOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """List model files of a given type, or counts across all types if omitted."""
    try:
        model_list.run_list(type_name=type, url=url, json_output=json_output)
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("find")
def find(
    name: Annotated[
        str, typer.Argument(help="Substring to search for (case-insensitive).")
    ],
    url: _UrlOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Case-insensitive search for a model name across all model types."""
    try:
        model_find.run_find(name=name, url=url, json_output=json_output)
    except ComfyError as err:
        backend.print_error_and_exit(err)
