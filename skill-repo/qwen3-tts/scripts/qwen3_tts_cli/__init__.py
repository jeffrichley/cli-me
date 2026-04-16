"""Agent-native CLI for Qwen3-TTS."""

import typer

app = typer.Typer(
    name="qwen3-tts-cli",
    help="Agent-native CLI for Qwen3-TTS — text-to-speech, voice cloning, voice design, and fine-tuning.",
    no_args_is_help=True,
)


def register_commands() -> None:
    """Register all command groups."""
    from . import generate, clone, design, info, finetune  # noqa: F401


register_commands()
