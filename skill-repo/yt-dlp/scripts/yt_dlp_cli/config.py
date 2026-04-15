"""Config command group — configuration helpers."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import run_command
from .commands import config_cookies, config_archive

config_app = typer.Typer(help="Manage cookies, archives, and output templates.", no_args_is_help=True)
app.add_typer(config_app, name="config")


@config_app.command()
def cookies(
    browser: Annotated[str, typer.Option(help="Browser to extract cookies from (chrome, firefox, edge, etc.)")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output cookies file path")] = "cookies.txt",
    profile: Annotated[Optional[str], typer.Option(help="Browser profile name")] = None,
    keyring: Annotated[Optional[str], typer.Option(help="Keyring backend")] = None,
    container: Annotated[Optional[str], typer.Option(help="Firefox container name")] = None,
) -> None:
    """Extract cookies from a browser for use with yt-dlp."""
    args = config_cookies.build_args(
        browser=browser,
        output=output,
        profile=profile,
        keyring=keyring,
        container=container,
    )
    run_command(args)


@config_app.command("archive-check")
def archive_check(
    archive_file: Annotated[str, typer.Argument(help="Path to the archive file")],
    url: Annotated[str, typer.Argument(help="URL to check against the archive")],
) -> None:
    """Check if a URL is already in a download archive. Prints video ID if NOT in archive (new). Prints nothing if already archived."""
    args = config_archive.build_check_args(archive_file, url)
    run_command(args)


@config_app.command("archive-add")
def archive_add(
    archive_file: Annotated[str, typer.Argument(help="Path to the archive file")],
    url: Annotated[str, typer.Argument(help="URL to add to the archive")],
) -> None:
    """Add a URL to a download archive without downloading."""
    args = config_archive.build_add_args(archive_file, url)
    run_command(args)
