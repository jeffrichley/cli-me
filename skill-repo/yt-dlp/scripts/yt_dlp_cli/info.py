"""Info command group — query/inspect without downloading."""

import subprocess
from typing import Annotated, Optional

import typer

from . import app
from .backend import run_command
from .commands import info_formats, info_metadata, info_subtitles, info_thumbnails, info_search
from .commands.search_providers import provider_names

info_app = typer.Typer(help="Query video info, formats, subtitles, and metadata.", no_args_is_help=True)
app.add_typer(info_app, name="info")


@info_app.command()
def formats(
    url: Annotated[str, typer.Argument(help="URL to inspect")],
    json: Annotated[bool, typer.Option("--json", "-j", help="Output full video metadata as JSON (instead of the human-readable format table)")] = False,
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


@info_app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    max_results: Annotated[int, typer.Option(help="Maximum number of results")] = 5,
    provider: Annotated[str, typer.Option(help=f"Search provider ({', '.join(provider_names())})")] = "youtube",
    pretty: Annotated[bool, typer.Option("--pretty", help="Human-readable output instead of JSON")] = False,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
) -> None:
    """Search for videos without downloading. Outputs JSON by default."""
    try:
        args = info_search.build_args(
            query,
            max_results=max_results,
            provider=provider,
            cookies=cookies,
        )
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)
    try:
        result = run_command(args, capture=True)
    except subprocess.CalledProcessError as e:
        typer.echo(e.stderr or f"Search failed (exit {e.returncode})", err=True)
        raise typer.Exit(code=e.returncode)
    output = info_search.format_output(
        info_search.parse_results(result.stdout),
        pretty=pretty,
    )
    typer.echo(output)
