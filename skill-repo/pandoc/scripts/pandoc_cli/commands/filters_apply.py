"""Logic for ``filters apply`` — run pandoc with ordered Lua/JSON filters.

Pandoc executes ``--lua-filter`` and ``--filter`` in the exact order they
appear on the command line, so this layer accepts a single ``ordered_filters``
list of ``(kind, path)`` tuples — preserving the order is the responsibility
of the dispatch layer in ``pandoc_cli/filters.py`` (which inspects ``sys.argv``).

See ``references/techniques/filters.md`` and ``gotchas.md`` for why ordering
matters (citeproc must see filter-introduced citations; pandoc-crossref must
run before citeproc; numbering filters last).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Literal

import typer

from pandoc_cli.backend import run_pandoc

FilterKind = Literal["lua", "json"]
FilterSpec = tuple[FilterKind, str]

# Pandoc's Lua filter API requires Block-element handlers (Header, Para, Div,
# BlockQuote, ...) to return Block values, and Inline-element handlers (Image,
# Span, Link, Str, ...) to return Inline values. When a handler returns the
# wrong tier, pandoc's runtime emits an error mentioning ``__toinline`` or
# ``__toblock`` (the internal coercion functions) — useful for the maintainer
# of pandoc, opaque for an agent. ``_LUA_TYPE_MISMATCH_HINT`` is appended to
# stderr when those tokens appear in pandoc's own error output.
_LUA_TYPE_MISMATCH_HINT = (
    "HINT: Lua filter type mismatch. A Block-element handler "
    "(Header, Para, Div) must return a Block; an Inline-element handler "
    "(Image, Span, Link) must return an Inline. See references/gotchas.md "
    "-> 'Lua Filter Type Matching'."
)


def build_args(
    *,
    input_path: str,
    output_path: str,
    ordered_filters: Iterable[FilterSpec],
    extra: Iterable[str] | None = None,
) -> list[str]:
    """Build the pandoc argv (without the ``pandoc`` executable itself).

    Layout: ``INPUT -o OUTPUT [--lua-filter P | --filter P ...] [extra...]``.
    Filter flags are emitted in the order given so pandoc applies them in CLI
    order. ``extra`` is appended verbatim for forwarded flags like
    ``--standalone`` or ``--from``.
    """
    argv: list[str] = [input_path, "-o", output_path]
    for kind, path in ordered_filters:
        if kind == "lua":
            argv.extend(["--lua-filter", path])
        elif kind == "json":
            argv.extend(["--filter", path])
        else:  # pragma: no cover — defensive; Literal makes this unreachable
            raise ValueError(f"Unknown filter kind: {kind!r}")
    if extra:
        argv.extend(extra)
    return argv


def run_apply(
    *,
    input_path: Path,
    output_path: Path,
    ordered_filters: Iterable[FilterSpec],
    extra: Iterable[str] | None = None,
) -> None:
    """Validate inputs/filters, then run pandoc with the constructed argv.

    Exits with code 1 (via ``typer.Exit``) before invoking pandoc when:
      - ``input_path`` does not exist
      - any filter path in ``ordered_filters`` does not exist

    The error messages name the missing path so agents can fix the typo
    without re-reading the failed command.
    """
    if not input_path.exists():
        typer.echo(f"ERROR: Input file not found: {input_path}", err=True)
        raise typer.Exit(code=1)

    materialized = list(ordered_filters)
    for kind, path in materialized:
        if not Path(path).exists():
            label = "Lua filter" if kind == "lua" else "JSON filter"
            typer.echo(f"ERROR: {label} not found: {path}", err=True)
            raise typer.Exit(code=1)

    argv = build_args(
        input_path=str(input_path),
        output_path=str(output_path),
        ordered_filters=materialized,
        extra=list(extra) if extra else None,
    )
    # Run with check=False so we can pattern-match on pandoc's stderr and
    # append the Lua-type-mismatch HINT when applicable. We let
    # ``run_pandoc`` forward stderr verbatim itself (its
    # ``forward_stderr_on_success=True`` default echoes captured stderr no
    # matter the returncode when ``check=False``), so we ONLY add the hint
    # here — re-echoing the body would double-print it.
    result = run_pandoc(
        argv,
        check=False,
        capture=True,
        forward_stderr_on_success=True,
    )
    if result.returncode != 0:
        if result.stderr and (
            "__toinline" in result.stderr or "__toblock" in result.stderr
        ):
            typer.echo(_LUA_TYPE_MISMATCH_HINT, err=True)
        raise typer.Exit(code=result.returncode)
