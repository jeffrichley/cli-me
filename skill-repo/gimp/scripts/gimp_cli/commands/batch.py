"""Batch command logic."""

from __future__ import annotations


def build_batch_args(
    commands: list[str],
    *,
    interpreter: str | None = None,
    new_instance: bool = True,
    no_interface: bool = True,
    console_messages: bool = True,
    no_splash: bool = True,
    no_data: bool = False,
    no_fonts: bool = False,
    verbose: bool = False,
    quit_after: bool = True,
    quit_via_flag: bool = True,
) -> list[str]:
    """Build deterministic, non-interactive GIMP batch argv."""
    args: list[str] = []
    if new_instance:
        args.append("--new-instance")
    if no_interface:
        args.append("--no-interface")
    if console_messages:
        args.append("--console-messages")
    if no_splash:
        args.append("--no-splash")
    if no_data:
        args.append("--no-data")
    if no_fonts:
        args.append("--no-fonts")
    if verbose:
        args.append("--verbose")
    if interpreter:
        args.extend(["--batch-interpreter", interpreter])
    for expr in commands:
        args.extend(["--batch", expr])
    if quit_after:
        if quit_via_flag:
            args.append("--quit")
        else:
            args.extend(["--batch", "(gimp-quit 0)"])
    return args
