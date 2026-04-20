"""sprite command group — stage 4 operations (final VN-ready sprites).

  @app.command("render") — render sprites for every (costume x emotion)
                           combination the character has on disk. No filter
                           — per Jeff's Phase 1 scope decision.
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console

from vnccs_cli import backend
from vnccs_cli.backend import VnccsError
from vnccs_cli.commands import sprite_render

app = typer.Typer(
    help="Render final VN-ready sprites for a VNCCS character.",
    no_args_is_help=True,
)

_console = Console()


@app.command("render")
def render(
    character: Annotated[str, typer.Argument(help="Character name (must exist on disk).")],
    seed: Annotated[
        Optional[int],
        typer.Option(
            "--seed",
            help="Reserved for future VNCCS releases — SpriteGenerator is deterministic today.",
        ),
    ] = None,
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    state_dir: Annotated[
        Optional[str],
        typer.Option("--state-dir", help="VNCCS state directory (overrides VNCCS_STATE_DIR env)."),
    ] = None,
    url: Annotated[
        Optional[str],
        typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Max seconds to wait (sprite render can take minutes)."),
    ] = 900.0,
    wait: Annotated[
        bool,
        typer.Option("--wait/--no-wait", help="Poll /history until finished."),
    ] = True,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON."),
    ] = False,
) -> None:
    """Render every (costume × emotion) sprite for CHARACTER (stage 4)."""
    try:
        result = sprite_render.run_render(
            character,
            seed=seed,
            comfy_path=path,
            state_dir=state_dir,
            url=url,
            wait=wait,
            timeout=timeout,
        )
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    _console.print(f"[bold cyan]{character}[/bold cyan] sprites submitted")
    _console.print(f"prompt_id: [green]{result['prompt_id']}[/green]")
