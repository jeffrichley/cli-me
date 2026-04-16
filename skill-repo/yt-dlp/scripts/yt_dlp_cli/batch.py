"""Batch command group — bulk operations and search."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import run_command
from .commands import batch_from_file, batch_sync, batch_search
from .commands.search_providers import provider_names

batch_app = typer.Typer(help="Batch downloads, incremental sync, and search.", no_args_is_help=True)
app.add_typer(batch_app, name="batch")


@batch_app.command("from-file")
def from_file(
    file: Annotated[str, typer.Argument(help="Path to file containing URLs (one per line)")],
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    archive: Annotated[Optional[str], typer.Option(help="Archive file to track downloaded videos")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    concurrent_fragments: Annotated[Optional[int], typer.Option("--concurrent-fragments", "-N", help="Concurrent fragment downloads")] = None,
    rate_limit: Annotated[Optional[str], typer.Option("--rate-limit", "-r", help="Rate limit (e.g., '50K', '1M')")] = None,
    sleep_interval: Annotated[Optional[float], typer.Option(help="Sleep seconds between downloads")] = None,
    max_sleep_interval: Annotated[Optional[float], typer.Option(help="Max random sleep seconds")] = None,
    max_downloads: Annotated[Optional[int], typer.Option(help="Stop after N downloads")] = None,
) -> None:
    """Download videos from a list of URLs in a file."""
    args = batch_from_file.build_args(
        file,
        format=format,
        output=output,
        output_dir=output_dir,
        archive=archive,
        cookies=cookies,
        concurrent_fragments=concurrent_fragments,
        rate_limit=rate_limit,
        sleep_interval=sleep_interval,
        max_sleep_interval=max_sleep_interval,
        max_downloads=max_downloads,
    )
    run_command(args)


@batch_app.command()
def sync(
    url: Annotated[str, typer.Argument(help="URL to sync (playlist, channel, etc.)")],
    archive: Annotated[str, typer.Option(help="Archive file to track downloaded videos")],
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    break_on_existing: Annotated[bool, typer.Option(help="Stop on already-downloaded video")] = False,
    sleep_interval: Annotated[Optional[float], typer.Option(help="Sleep seconds between downloads")] = None,
    max_sleep_interval: Annotated[Optional[float], typer.Option(help="Max random sleep seconds")] = None,
    max_downloads: Annotated[Optional[int], typer.Option(help="Stop after N downloads")] = None,
) -> None:
    """Incrementally sync a playlist or channel using an archive file."""
    args = batch_sync.build_args(
        url,
        archive=archive,
        format=format,
        output=output,
        output_dir=output_dir,
        cookies=cookies,
        break_on_existing=break_on_existing,
        sleep_interval=sleep_interval,
        max_sleep_interval=max_sleep_interval,
        max_downloads=max_downloads,
    )
    run_command(args)


@batch_app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    max_results: Annotated[int, typer.Option(help="Maximum number of results")] = 5,
    provider: Annotated[str, typer.Option(help=f"Search provider ({', '.join(provider_names())})")] = "youtube",
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
) -> None:
    """Search and download the results."""
    try:
        args = batch_search.build_args(
            query,
            max_results=max_results,
            provider=provider,
            output=output,
            output_dir=output_dir,
            format=format,
            cookies=cookies,
        )
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)
    run_command(args)
