"""Agent-native CLI for yt-dlp."""

import typer

app = typer.Typer(
    name="yt-dlp-cli",
    help="Agent-native CLI for yt-dlp — download, extract, and process video/audio.",
    no_args_is_help=True,
)


def register_commands() -> None:
    """Register all command groups."""
    from . import download, info, config, process, batch  # noqa: F401


register_commands()
