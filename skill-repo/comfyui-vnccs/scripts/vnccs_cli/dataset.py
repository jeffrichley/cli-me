"""dataset command group — stage 5 operations (LoRA training dataset export).

Phase 3 populates:
  @app.command("preview") — dry-run; show what export WOULD produce (Wave 1)
  @app.command("export")  — package sprites + captions into a kohya-style
                            dataset directory (Wave 2, not yet implemented)
"""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from vnccs_cli import backend
from vnccs_cli.backend import VnccsError
from vnccs_cli.commands import dataset_export, dataset_preview

app = typer.Typer(
    help="Export VNCCS-generated sprites as LoRA training datasets.",
    no_args_is_help=True,
)

_console = Console()


@app.command("preview")
def preview(
    character: Annotated[
        str,
        typer.Argument(help="VNCCS character name (directory under VN_CharacterCreatorSuit/)."),
    ],
    game_name: Annotated[
        Optional[str],
        typer.Option(
            "--game-name",
            help="kohya caption prefix / folder tag (default: 'VN'). Matches DatasetGenerator.game_name.",
        ),
    ] = None,
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    state_dir: Annotated[
        Optional[str],
        typer.Option(
            "--state-dir",
            help="VNCCS state directory (overrides VNCCS_STATE_DIR env; default <COMFY_PATH>/output/VN_CharacterCreatorSuit).",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a Rich table."),
    ] = False,
) -> None:
    """Dry-run `dataset export` for CHARACTER — no files are created.

    Reports face count, sprite count, total pair count, would-be output
    layout, and a sample of interleaved face+sprite filenames so you can
    sanity-check the export before committing to the full stage-5 run.
    Pure filesystem inspection; no ComfyUI HTTP calls.
    """
    try:
        result = dataset_preview.run_preview(
            character,
            game_name=game_name,
            comfy_path=path,
            state_dir=state_dir,
        )
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(dataset_preview.format_json(result))
        return

    layout = result["output_layout"]
    summary = Table(
        title=f"dataset preview — {result['character']} (dry-run)",
        show_header=True,
        header_style="bold cyan",
    )
    summary.add_column("Field", style="cyan", no_wrap=True)
    summary.add_column("Value")
    summary.add_row("character (dir)", result["character"])
    summary.add_row("character (name)", result["character_name"])
    summary.add_row("game-name", result["game_name"])
    summary.add_row("faces found", str(result["face_count"]))
    summary.add_row("sprites found", str(result["sprite_count"]))
    summary.add_row("total pairs", str(result["pair_count"]))
    summary.add_row("caption files", str(result["caption_count"]))
    summary.add_row("output lora dir", layout["lora_dir"])
    summary.add_row("face filename pattern", layout["face_filename_pattern"])
    summary.add_row("sprite filename pattern", layout["sprite_filename_pattern"])
    summary.add_row("caption prefix", layout["caption_prefix"])
    _console.print(summary)

    samples = result["samples"]
    total = result["total_samples"]
    if samples:
        _console.print(f"\n[bold]Samples[/bold] (showing {len(samples)} of {total}):")
        for name in samples:
            _console.print(f"  - {name}")
        remaining = total - len(samples)
        if remaining > 0:
            _console.print(f"  [dim]... and {remaining} more[/dim]")

    _console.print(
        "\n[dim]No files written — this is a dry-run. "
        "Run `vnccs dataset export` to produce the kohya-ss dataset.[/dim]"
    )


@app.command("export")
def export(
    character: Annotated[str, typer.Argument(help="Character name (must exist on disk).")],
    out: Annotated[
        Optional[str],
        typer.Option(
            "--out",
            help="Destination dir — VNCCS's lora/ tree is copied here after completion.",
        ),
    ] = None,
    game_name: Annotated[
        Optional[str],
        typer.Option(
            "--game-name",
            help="kohya caption prefix / folder tag (default: 'VN'). Matches DatasetGenerator.game_name.",
        ),
    ] = None,
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    state_dir: Annotated[
        Optional[str],
        typer.Option("--state-dir", help="VNCCS state directory (overrides VNCCS_STATE_DIR env)."),
    ] = None,
    url: Annotated[
        Optional[str],
        typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Max seconds to wait."),
    ] = 900.0,
    wait: Annotated[
        bool,
        typer.Option("--wait/--no-wait", help="Poll /history until finished (required for --out)."),
    ] = True,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON."),
    ] = False,
) -> None:
    """Submit stage-5 dataset workflow; copy VNCCS's lora/ to --out on success."""
    try:
        result = dataset_export.run_export(
            character,
            out=out,
            game_name=game_name,
            comfy_path=path,
            state_dir=state_dir,
            url=url,
            wait=wait,
            timeout=timeout,
        )
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    _console.print(
        f"[bold cyan]{character}[/bold cyan] dataset (game=[magenta]{result['game_name']}[/magenta]) submitted"
    )
    sub = result["submission"]
    _console.print(f"prompt_id: [green]{sub['prompt_id']}[/green]")
    if "out" in result:
        stats = result["copy_stats"]
        _console.print(
            f"copied to [bold]{result['out']}[/bold]: "
            f"{stats['png_count']} PNGs + {stats['txt_count']} captions"
        )
