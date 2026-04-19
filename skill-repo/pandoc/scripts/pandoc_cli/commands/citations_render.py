"""citations render — logic layer.

Builds and runs `pandoc --citeproc --bibliography BIB ...` invocations.

Design choice — `--natbib` and `--biblatex` are intentionally NOT exposed as
flags on this subcommand. Per `references/gotchas.md`, those three flags
(`--citeproc`, `--natbib`, `--biblatex`) are conceptually mutually exclusive
ways to handle citations, but pandoc 3.9.0.2 accepts the combination silently
and the last one wins, which produces unpredictable output. To keep this
subcommand focused and predictable, `citations render` always uses
`--citeproc`. Users who want natbib/biblatex emission should reach for
`convert to` and pass `--metadata cite-method=natbib` (or `biblatex`)
themselves; the rendering technique page documents that workflow.

The dispatch layer (`pandoc_cli/citations.py`) is a thin Typer wrapper that
calls into `build_args` / `run_render` here. That split keeps the argv
construction independently testable without driving Typer.
"""

from __future__ import annotations

from pathlib import Path

import typer

from pandoc_cli.backend import report_success, run_pandoc


def build_args(
    input: str,
    output: str,
    bibliography: str,
    *,
    csl: str | None = None,
    from_: str | None = None,
    to: str | None = None,
    standalone: bool | None = None,
    metadata: list[str] | None = None,
) -> list[str]:
    """Construct the pandoc argv for a `citations render` invocation.

    The argv always includes `--citeproc` and `--bibliography BIB`. Optional
    flags are appended only when the caller supplies them so that pandoc's
    default behavior is preserved when the user doesn't override it.

    Argument order: INPUT first, then `-o OUTPUT`, then citation flags, then
    pass-through flags. The placement of `--citeproc` matches the convention
    documented in `references/gotchas.md` (filters run in CLI order; citeproc
    last lets any preceding filter inject citations into the AST).

    Note on `--standalone`: pandoc auto-enables standalone mode for binary
    output formats (PDF, DOCX, EPUB, etc.), so this wrapper deliberately
    does NOT inject `--standalone` based on the output extension. The flag
    is only added when the caller passes ``standalone=True``. Users who
    want a standalone HTML must pass `--standalone` explicitly (HTML
    defaults to fragment mode in pandoc).
    """
    args: list[str] = [input, "-o", output]

    if from_ is not None:
        args.extend(["--from", from_])
    if to is not None:
        args.extend(["--to", to])

    if standalone is True:
        args.append("--standalone")
    elif standalone is False:
        args.append("--no-standalone")

    args.extend(["--bibliography", bibliography])
    if csl is not None:
        args.extend(["--csl", csl])

    if metadata:
        for item in metadata:
            args.extend(["--metadata", item])

    args.append("--citeproc")
    return args


def run_render(
    input: str,
    output: str,
    bibliography: str,
    *,
    csl: str | None = None,
    from_: str | None = None,
    to: str | None = None,
    standalone: bool | None = None,
    metadata: list[str] | None = None,
) -> None:
    """Validate preconditions and dispatch to pandoc.

    Pre-flight checks (each failure exits 1 before invoking pandoc):
      * INPUT exists
      * BIB exists  (pandoc would also error, but our message is clearer
        and we want to fail before paying subprocess cost)
      * BIB is not a binary EndNote `.enl` file (pandoc would emit an
        opaque parser error; we surface a targeted hint from
        ``references/gotchas.md`` instead)
      * CSL exists when `--csl` is passed (pandoc would emit a 6-line
        Haskell `withBinaryFile` traceback; we exit cleanly with a
        targeted message)

    Pandoc's own errors (malformed BibTeX, citation key not found, write
    failures) are surfaced verbatim from `run_pandoc`. The wrapper preserves
    pandoc's exit code rather than always returning 1.
    """
    in_path = Path(input)
    if not in_path.exists():
        typer.echo(f"ERROR: Input file not found: {input}", err=True)
        raise typer.Exit(code=1)

    bib_path = Path(bibliography)
    if not bib_path.exists():
        typer.echo(f"ERROR: Bibliography file not found: {bibliography}", err=True)
        raise typer.Exit(code=1)
    # .enl is EndNote's proprietary binary format; pandoc cannot parse it.
    # Surface the targeted hint from gotchas.md before paying subprocess cost.
    if bib_path.suffix.lower() == ".enl":
        typer.echo(
            "ERROR: .enl is binary EndNote format, not bibliography. "
            "Convert to BibTeX or CSL-JSON first (e.g. via Zotero with "
            "Better BibTeX).",
            err=True,
        )
        raise typer.Exit(code=1)

    if csl is not None:
        csl_path = Path(csl)
        if not csl_path.exists():
            typer.echo(f"ERROR: CSL file not found: {csl}", err=True)
            raise typer.Exit(code=1)

    args = build_args(
        input,
        output,
        bibliography,
        csl=csl,
        from_=from_,
        to=to,
        standalone=standalone,
        metadata=metadata,
    )

    # check=False so pandoc warnings (e.g. "citation key not found") that exit
    # 0 surface their stderr; non-zero exits still propagate via the wrapper.
    # backend.run_pandoc forwards stderr on success by default, so the
    # explicit echo below is for the rare case where check=False returns a
    # non-zero proc with stderr we still want surfaced before re-raising.
    proc = run_pandoc(args, check=False)
    if proc.returncode != 0:
        if proc.stderr:
            typer.echo(proc.stderr, err=True, nl=False)
        raise typer.Exit(code=proc.returncode)

    report_success(output)
