"""Info command group — query/inspect without downloading."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import run_command
from .commands import info_formats, info_metadata, info_subtitles, info_thumbnails

info_app = typer.Typer(help="Query video info, formats, subtitles, and metadata.", no_args_is_help=True)
app.add_typer(info_app, name="info")


@info_app.command()
def formats(
    url: Annotated[str, typer.Argument(help="URL to inspect")],
    json: Annotated[bool, typer.Option("--json", "-j", help="Output format details as JSON")] = False,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
) -> None:
    """List available formats for a URL."""
    if json:
        args = info_formats.build_json_args(url, cookies=cookies)
    else:
        args = info_formats.build_args(url, cookies=cookies)
    run_command(args)


@info_app.command()
def metadata(
    url: Annotated[str, typer.Argument(help="URL to inspect")],
    write_json: Annotated[bool, typer.Option(help="Write .info.json file instead of printing to stdout")] = False,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory for .info.json")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
) -> None:
    """Dump video metadata as JSON."""
    args = info_metadata.build_args(
        url,
        write_json=write_json,
        output_dir=output_dir,
        cookies=cookies,
    )
    run_command(args)


@info_app.command()
def subtitles(
    url: Annotated[str, typer.Argument(help="URL to inspect")],
    download: Annotated[bool, typer.Option(help="Download subtitle files instead of listing")] = False,
    auto_subs: Annotated[bool, typer.Option("--auto-subs", help="Include auto-generated subtitles (requires --download)")] = False,
    langs: Annotated[Optional[str], typer.Option("--langs", help="Subtitle languages to filter (e.g., 'en,es')")] = None,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Subtitle format (e.g., 'srt', 'vtt', 'ass')")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
) -> None:
    """List or download subtitles for a URL."""
    args = info_subtitles.build_args(
        url,
        download=download,
        auto_subs=auto_subs,
        langs=langs,
        format=format,
        cookies=cookies,
    )
    run_command(args)


@info_app.command()
def thumbnails(
    url: Annotated[str, typer.Argument(help="URL to inspect")],
    download: Annotated[bool, typer.Option(help="Download thumbnail instead of listing")] = False,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    convert: Annotated[Optional[str], typer.Option(help="Convert thumbnail to format (e.g., 'jpg', 'png', 'webp')")] = None,
) -> None:
    """List or download thumbnails for a URL."""
    args = info_thumbnails.build_args(
        url,
        download=download,
        cookies=cookies,
        convert=convert,
    )
    run_command(args)
