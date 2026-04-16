"""Agent-native CLI for Demucs music source separation."""

import typer

app = typer.Typer(
    name="demucs-cli",
    help="Agent-native CLI for Demucs — separate audio into stems (vocals, drums, bass, other).",
    no_args_is_help=True,
)


def register_commands() -> None:
    """Register all command groups."""
    from . import separate, models  # noqa: F401


register_commands()
