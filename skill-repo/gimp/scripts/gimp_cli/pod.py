"""Print-on-demand convenience command group."""

from __future__ import annotations

import typer

from gimp_cli import app
from gimp_cli.backend import detect_version, run_command
from gimp_cli.commands.pod import (
    build_fit_crop_expression,
    build_pod_batch_args,
    build_prep_expression,
    build_resize_expression,
)

pod_app = typer.Typer(help="Use when you need POD-focused image prep commands.")
app.add_typer(pod_app, name="pod")


def _run_expression(
    *,
    expression: str,
    no_data: bool,
    no_fonts: bool,
    verbose: bool,
    keep_alive: bool,
) -> None:
    version_text = detect_version()
    args = build_pod_batch_args(
        expression=expression,
        no_data=no_data,
        no_fonts=no_fonts,
        verbose=verbose,
        keep_alive=keep_alive,
        gimp_version_text=version_text,
    )
    result = run_command(args, check=False)
    if result.stdout:
        typer.echo(result.stdout, nl=False)
    if result.stderr:
        typer.echo(result.stderr, err=True, nl=False)
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


@pod_app.command("resize")
def resize(
    input_path: str = typer.Option(..., "--input", help="Input image path."),
    output_path: str = typer.Option(..., "--output", help="Output image path."),
    width: int = typer.Option(..., "--width", help="Target width in pixels."),
    height: int = typer.Option(..., "--height", help="Target height in pixels."),
    interpolation: str = typer.Option("cubic", "--interpolation", help="none|linear|cubic|lanczos"),
    flatten: bool = typer.Option(False, "--flatten", help="Flatten image before save."),
    no_data: bool = typer.Option(False, "--no-data", help="Skip brushes/gradients load."),
    no_fonts: bool = typer.Option(False, "--no-fonts", help="Skip fonts load."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose GIMP logs."),
    keep_alive: bool = typer.Option(False, "--keep-alive", help="Do not auto-quit after run."),
) -> None:
    """Resize artwork to exact pixel dimensions."""
    expression = build_resize_expression(
        input_path=input_path,
        output_path=output_path,
        width=width,
        height=height,
        interpolation=interpolation,
        flatten=flatten,
    )
    _run_expression(
        expression=expression,
        no_data=no_data,
        no_fonts=no_fonts,
        verbose=verbose,
        keep_alive=keep_alive,
    )


@pod_app.command("fit-crop")
def fit_crop(
    input_path: str = typer.Option(..., "--input", help="Input image path."),
    output_path: str = typer.Option(..., "--output", help="Output image path."),
    width: int = typer.Option(..., "--width", help="Target width in pixels."),
    height: int = typer.Option(..., "--height", help="Target height in pixels."),
    anchor: str = typer.Option("center", "--anchor", help="center|top|bottom|left|right"),
    flatten: bool = typer.Option(False, "--flatten", help="Flatten image before save."),
    no_data: bool = typer.Option(False, "--no-data", help="Skip brushes/gradients load."),
    no_fonts: bool = typer.Option(False, "--no-fonts", help="Skip fonts load."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose GIMP logs."),
    keep_alive: bool = typer.Option(False, "--keep-alive", help="Do not auto-quit after run."),
) -> None:
    """Scale-to-fill then crop to product ratio."""
    expression = build_fit_crop_expression(
        input_path=input_path,
        output_path=output_path,
        width=width,
        height=height,
        anchor=anchor,
        flatten=flatten,
    )
    _run_expression(
        expression=expression,
        no_data=no_data,
        no_fonts=no_fonts,
        verbose=verbose,
        keep_alive=keep_alive,
    )


@pod_app.command("prep")
def prep(
    input_path: str = typer.Option(..., "--input", help="Input image path."),
    output_path: str = typer.Option(..., "--output", help="Output image path."),
    width: int = typer.Option(..., "--width", help="Target width in pixels."),
    height: int = typer.Option(..., "--height", help="Target height in pixels."),
    dpi: int = typer.Option(300, "--dpi", help="Target print DPI metadata."),
    flatten: bool = typer.Option(True, "--flatten", help="Flatten image before save."),
    no_data: bool = typer.Option(False, "--no-data", help="Skip brushes/gradients load."),
    no_fonts: bool = typer.Option(False, "--no-fonts", help="Skip fonts load."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose GIMP logs."),
    keep_alive: bool = typer.Option(False, "--keep-alive", help="Do not auto-quit after run."),
) -> None:
    """One-shot POD prep: scale + DPI + export-ready save."""
    expression = build_prep_expression(
        input_path=input_path,
        output_path=output_path,
        width=width,
        height=height,
        dpi=dpi,
        flatten=flatten,
    )
    _run_expression(
        expression=expression,
        no_data=no_data,
        no_fonts=no_fonts,
        verbose=verbose,
        keep_alive=keep_alive,
    )
