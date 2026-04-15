# Typer CLI Template

Use this as the starting point for every skill's scripts/ directory.
Each skill's scripts/ is self-contained — it has its own pyproject.toml
so `uv run` works without the cli-me repo.

**IMPORTANT: The CLI is a package, not a single file.** Split commands
into modules by group from the start. One file per command group keeps
files focused and enables parallel agent work.

## scripts/pyproject.toml

```toml
[project]
name = "{{name}}-cli"
version = "0.1.0"
description = "Agent-native CLI for {{Software Name}}"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15.0",
    "rich>=13.0.0",
]

[project.scripts]
{{name}}-cli = "{{name}}_cli:app"
```

## Package Structure

```
scripts/
├── pyproject.toml
└── {{name}}_cli/
    ├── __init__.py       # Exports `app`, registers all sub-apps
    ├── __main__.py       # `python -m {{name}}_cli` support
    ├── backend.py        # find_executable, detect_version, run helpers
    ├── convert.py        # Convert command group (example)
    ├── extract.py        # Extract command group (example)
    └── ...               # One file per command group
```

## scripts/{{name}}_cli/__init__.py

```python
"""{{name}}_cli: Agent-native CLI for {{Software Name}}.

Calls the real {{Software}} executable — does not reimplement functionality.
"""

import typer

app = typer.Typer(
    name="{{name}}-cli",
    help="Agent-native CLI for {{Software Name}}.",
    no_args_is_help=True,
)

# Import and register command groups
from {{name}}_cli.convert import convert_app
from {{name}}_cli.extract import extract_app
# ... add more as needed

app.add_typer(convert_app, name="convert")
app.add_typer(extract_app, name="extract")
# ... add more as needed
```

## scripts/{{name}}_cli/__main__.py

```python
"""Allow running as `python -m {{name}}_cli`."""

from {{name}}_cli import app

app()
```

## scripts/{{name}}_cli/backend.py

```python
"""Backend helpers: find executable, detect version, run commands."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def find_executable(name: str = "{{executable}}") -> str:
    """Locate the {{Software}} executable or exit with install instructions."""
    path = shutil.which(name)
    if path is None:
        err_console.print(
            f"[bold red]ERROR:[/] {name} not found in PATH.\n"
            "Install with: {{install_command}}",
        )
        raise typer.Exit(code=1)
    return path


def detect_version() -> tuple[int, ...]:
    """Detect installed {{Software}} version."""
    exe = find_executable()
    result = subprocess.run(
        [exe, "{{version_flag}}"],
        capture_output=True,
        text=True,
    )
    # Parse version — adapt this to the software's output format
    version_str = result.stdout.strip().split()[-1]
    return tuple(int(x) for x in version_str.split("."))


def run_command(
    args: list[str], check: bool = True
) -> subprocess.CompletedProcess:
    """Run a {{Software}} command and return the result."""
    exe = find_executable()
    cmd = [exe] + args
    typer.echo(f"Running: {' '.join(cmd)}", err=True)
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def report_success(output_path: str) -> None:
    """Report successful output with file size."""
    path = Path(output_path)
    if path.exists():
        size = path.stat().st_size
        if size > 1_000_000:
            size_str = f"{size / 1_000_000:.1f} MB"
        elif size > 1_000:
            size_str = f"{size / 1_000:.1f} KB"
        else:
            size_str = f"{size} bytes"
        console.print(f"Output: {output_path} ({size_str})", style="green")
    else:
        console.print(f"Output: {output_path}", style="green")
```

## scripts/{{name}}_cli/convert.py (example command group)

```python
"""Convert command group."""

from __future__ import annotations

import typer

from {{name}}_cli.backend import find_executable, run_command, report_success

convert_app = typer.Typer(help="Format conversion and compression")


@convert_app.command("format")
def convert_format(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    codec: str = typer.Option("libx264", "--codec", "-c", help="Video codec"),
    crf: int = typer.Option(23, "--crf", help="Quality (lower=better)"),
    copy: bool = typer.Option(False, "--copy", help="Stream copy (no re-encode)"),
) -> None:
    """Convert between formats with optional re-encoding."""
    if copy:
        args = ["-i", input, "-c", "copy", "-movflags", "+faststart", output]
    else:
        args = [
            "-i", input,
            "-c:v", codec, "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output,
        ]
    run_command(args)
    report_success(output)
```

Follow this pattern for each command group. One file, one Typer sub-app,
imported and registered in `__init__.py`.
