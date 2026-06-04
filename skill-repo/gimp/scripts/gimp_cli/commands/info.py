"""Info command logic."""

from __future__ import annotations


def build_version_args() -> list[str]:
    """Build args for version lookup."""
    return ["--version"]


def capability_flags() -> list[str]:
    """Return core automation flags supported by this wrapper."""
    return [
        "--new-instance",
        "--no-interface",
        "--console-messages",
        "--no-splash",
        "--batch-interpreter",
        "--batch",
        "--quit",
    ]
