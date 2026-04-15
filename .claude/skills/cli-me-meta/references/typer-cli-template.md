# Typer CLI Template

Use this as the starting point for every skill's scripts/ directory.
Each skill's scripts/ is self-contained — it has its own pyproject.toml
so `uv run` works without the cli-me repo.

## scripts/pyproject.toml

```toml
[project]
name = "{{name}}-cli"
version = "0.1.0"
description = "Agent-native CLI for {{Software Name}}"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15.0",
]

[project.scripts]
{{name}}-cli = "{{name}}_cli:app"
```

## scripts/{{name}}_cli.py

```python
"""{{name}}_cli: Agent-native CLI for {{Software Name}}.

Calls the real {{Software}} executable — does not reimplement functionality.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="{{name}}-cli",
    help="Agent-native CLI for {{Software Name}}.",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

def find_executable() -> str:
    """Locate the {{Software}} executable or exit with install instructions."""
    path = shutil.which("{{executable}}")
    if path is None:
        typer.echo(
            "ERROR: {{Software}} not found in PATH.\n"
            "Install with: {{install_command}}",
            err=True,
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
    # Example: "GIMP 2.10.38" → (2, 10, 38)
    version_str = result.stdout.strip().split()[-1]
    return tuple(int(x) for x in version_str.split("."))


def run_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a {{Software}} command and return the result."""
    exe = find_executable()
    return subprocess.run(
        [exe] + args,
        capture_output=True,
        text=True,
        check=check,
    )


# ---------------------------------------------------------------------------
# Commands — add command groups matching the software's workflow domains
# ---------------------------------------------------------------------------

@app.command()
def version() -> None:
    """Show the installed {{Software}} version."""
    v = detect_version()
    typer.echo(f"{{Software}} {'.'.join(str(x) for x in v)}")


# Add more commands here based on the research phase findings.
# Group related commands using typer.Typer() sub-apps if needed.

if __name__ == "__main__":
    app()
```
