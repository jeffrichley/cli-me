"""workflow group — run, parameterize, validate, and extract workflow JSON."""

from pathlib import Path
from typing import Annotated, List, Optional

import typer

from comfyui_cli import backend
from comfyui_cli.backend import ComfyError
from comfyui_cli.commands import workflow_extract as _extract_cmd
from comfyui_cli.commands import workflow_run as _run_cmd
from comfyui_cli.commands import workflow_set as _set_cmd
from comfyui_cli.commands import workflow_validate as _validate_cmd

app = typer.Typer(
    help="Run, parameterize, validate, and extract workflow JSON.",
    no_args_is_help=True,
)


_UrlOpt = Annotated[
    Optional[str],
    typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
]


@app.command("run")
def run(
    file: Annotated[
        Path,
        typer.Argument(help="Workflow file: .json (API or UI), or .png/.webp with embedded workflow."),
    ],
    url: _UrlOpt = None,
    live: Annotated[
        bool,
        typer.Option(
            "--live/--no-live",
            help="Stream /ws progress events during execution (default: on).",
        ),
    ] = True,
    output_dir: Annotated[
        Optional[Path],
        typer.Option("--output-dir", help="Directory to download output images to."),
    ] = None,
    client_id: Annotated[
        Optional[str],
        typer.Option(
            "--client-id",
            help="Stable client_id shared between /prompt submit and /ws watch.",
        ),
    ] = None,
    front: Annotated[
        bool,
        typer.Option("--front", help="Enqueue ahead of existing pending items."),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Overall timeout in seconds."),
    ] = 600.0,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON summary instead of a table."),
    ] = False,
) -> None:
    """Submit a workflow, wait for it to finish, and download outputs."""
    try:
        _run_cmd.run_run(
            file=file,
            url=url,
            live=live,
            output_dir=output_dir,
            client_id=client_id,
            front=front,
            timeout=timeout,
            json_output=json_output,
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)


@app.command("set")
def set_cmd(
    file: Annotated[Path, typer.Argument(help="Input workflow JSON.")],
    param: Annotated[
        Optional[List[str]],
        typer.Option(
            "--param",
            help=(
                "KEY=VAL pair. KEY forms: NODE_ID.key, @Title.key, class:ClassName.key. "
                "Special values: seed=random, seed=random64. Repeatable."
            ),
        ),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output", "-o", help="Write patched workflow here (default: stdout)."
        ),
    ] = None,
    inline: Annotated[
        bool,
        typer.Option(
            "--inline",
            help="Rewrite the input file in place. Mutually exclusive with -o.",
        ),
    ] = False,
) -> None:
    """Substitute parameters in a workflow JSON and emit the patched version."""
    _set_cmd.run_set(
        in_file=file,
        params=param or [],
        out_file=output,
        inline=inline,
    )


@app.command("validate")
def validate(
    file: Annotated[Path, typer.Argument(help="Workflow JSON to validate.")],
) -> None:
    """Detect UI vs API format; check class_types are non-empty and links resolve."""
    _validate_cmd.run_validate(file=file)


@app.command("extract")
def extract(
    image: Annotated[Path, typer.Argument(help="PNG or WebP image with embedded workflow.")],
    ui: Annotated[
        bool,
        typer.Option("--ui", help="Extract the UI-format workflow only."),
    ] = False,
    api: Annotated[
        bool,
        typer.Option("--api", help="Extract the API-format workflow (prompt) only."),
    ] = False,
    both: Annotated[
        bool,
        typer.Option("--both", help="Extract both formats."),
    ] = False,
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output", "-o", help="Write extracted workflow here (default: stdout)."
        ),
    ] = None,
) -> None:
    """Pull an embedded workflow from a PNG (tEXt/iTXt) or WebP (EXIF) image."""
    _extract_cmd.run_extract(
        image=image, ui=ui, api=api, both=both, out_file=output
    )
