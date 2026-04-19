"""filters command group — thin CLI dispatch.

  @filters_app.command("apply") — convert with --lua-filter / --filter
  @filters_app.command("crossref-check") — verify pandoc-crossref present

CLI order across the two filter flag types is preserved by walking
``sys.argv`` (Typer collapses each repeatable option into its own list and
loses the relative order). See references/techniques/filters.md for why
ordering is load-bearing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from pandoc_cli import filters_app
from pandoc_cli.commands.filters_apply import FilterSpec, run_apply
from pandoc_cli.commands.filters_crossref import run_crossref_check


def _ordered_filters_from_argv(
    argv: list[str],
    lua_filters: list[str],
    json_filters: list[str],
) -> list[FilterSpec]:
    """Reconstruct CLI order of ``--lua-filter`` and ``--filter`` flags.

    Walks ``argv`` from left to right. Whenever it sees ``--lua-filter`` or
    ``--filter`` (with the path either as the next token or joined via ``=``),
    it appends the corresponding spec.

    Programmatic-invocation fallback
    --------------------------------
    When ``argv`` does NOT carry the filter flags (e.g. the command was
    invoked from Python via ``CliRunner`` with a different argv, or from a
    test that constructs ``lua_filters``/``json_filters`` directly), the
    walker finds nothing. In that case the function falls back to
    concatenating ``lua_filters`` then ``json_filters`` — meaning ALL Lua
    filters run BEFORE all JSON filters, regardless of how the caller
    intended to interleave them. The original CLI order is LOST.

    If you call this programmatically and need a specific lua/json
    interleaving, build an explicit ordered ``list[FilterSpec]`` and pass it
    straight to ``commands.filters_apply.run_apply`` rather than going
    through this dispatch helper.
    """
    ordered: list[FilterSpec] = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--lua-filter" and i + 1 < len(argv):
            ordered.append(("lua", argv[i + 1]))
            i += 2
            continue
        if token.startswith("--lua-filter="):
            ordered.append(("lua", token.split("=", 1)[1]))
            i += 1
            continue
        if token == "--filter" and i + 1 < len(argv):
            ordered.append(("json", argv[i + 1]))
            i += 2
            continue
        if token.startswith("--filter="):
            ordered.append(("json", token.split("=", 1)[1]))
            i += 1
            continue
        i += 1

    # Fallback: programmatic invocation where sys.argv doesn't carry the flags.
    if not ordered and (lua_filters or json_filters):
        ordered = [("lua", p) for p in lua_filters] + [("json", p) for p in json_filters]
    return ordered


@filters_app.command("apply")
def apply(
    input: Path = typer.Argument(..., help="Input document"),
    output: Path = typer.Argument(..., help="Output path"),
    lua_filter: list[str] = typer.Option(
        None,
        "--lua-filter",
        help="Path to a Lua filter (.lua). Repeatable; preserves CLI order vs --filter.",
    ),
    filter: list[str] = typer.Option(
        None,
        "--filter",
        help="Path to a JSON filter program. Repeatable; preserves CLI order vs --lua-filter.",
    ),
    from_: Optional[str] = typer.Option(None, "--from", "-f", help="Input format"),
    to: Optional[str] = typer.Option(None, "--to", "-t", help="Output format"),
    standalone: Optional[bool] = typer.Option(
        None,
        "--standalone/--no-standalone",
        help="Wrap in a standalone document (template/header).",
    ),
) -> None:
    """Convert ``INPUT`` to ``OUTPUT`` applying filters in CLI order.

    Pandoc executes ``--lua-filter`` and ``--filter`` in command-line order;
    the ordering is preserved here by inspecting ``sys.argv`` directly so
    interleaved usage like ``--lua-filter a.lua --filter b --lua-filter c.lua``
    runs exactly as written.
    """
    ordered = _ordered_filters_from_argv(
        sys.argv,
        lua_filter or [],
        filter or [],
    )

    extra: list[str] = []
    if from_:
        extra.extend(["--from", from_])
    if to:
        extra.extend(["--to", to])
    if standalone is True:
        extra.append("--standalone")
    elif standalone is False:
        extra.append("--no-standalone")

    run_apply(
        input_path=input,
        output_path=output,
        ordered_filters=ordered,
        extra=extra or None,
    )
    typer.echo(f"Wrote: {output}")


@filters_app.command("crossref-check")
def crossref_check() -> None:
    """Verify pandoc-crossref is installed; print path + version."""
    info = run_crossref_check()
    typer.echo(f"path:    {info['path']}")
    typer.echo(f"version: {info['version']}")
