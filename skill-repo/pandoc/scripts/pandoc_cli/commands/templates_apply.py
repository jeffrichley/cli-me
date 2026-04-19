"""Logic for `templates apply` — convert with `--template TEMPLATE`.

Split into `build_args` (pure: input/output/template/options -> argv list) and
`run_apply` (impure: validates preconditions, warns on binary outputs, shells
out via the backend). Tier 1 tests assert the exact argv; Tier 2 tests run
the real binary end-to-end.

Notes on flag semantics (mirrors templates.md):

- ``--template`` is for text-based output formats only (LaTeX, HTML, Markdown,
  RTF). For DOCX/ODT/PPTX/EPUB, pandoc silently ignores `--template` and you
  want ``--reference-doc`` (DOCX/ODT/PPTX) or an EPUB-specific styling flag
  instead. We warn (do NOT block) when the output extension is one of those
  — the user may genuinely have a reason.
- ``--variable KEY=VALUE`` (`-V`) is repeatable; each entry forwards
  verbatim, letting pandoc parse `key=value`.
- ``--metadata KEY=VALUE`` (`-M`) is repeatable; same forwarding rule.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pandoc_cli.backend import report_success, run_pandoc

# Output suffixes where `--template` is silently ignored by pandoc — the
# DOCX/ODT/PPTX writers consume `--reference-doc` instead, and EPUB uses its
# own styling pipeline (`--css`, `--epub-stylesheet`, `--epub-cover-image`,
# etc.) rather than a string template.
_REFERENCE_DOC_SUFFIXES = {".docx", ".odt", ".pptx", ".epub"}


def build_args(
    input: str,
    output: str,
    template: str,
    *,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    variable: Optional[list[str]] = None,
    metadata: Optional[list[str]] = None,
) -> list[str]:
    """Construct the pandoc argv list for a `templates apply` invocation.

    Pure function: no filesystem checks, no subprocess calls. Tests assert
    against the returned list directly.
    """
    args: list[str] = [str(input), "-o", str(output), "--template", str(template)]

    if from_ is not None:
        args.extend(["--from", from_])
    if to is not None:
        args.extend(["--to", to])

    for entry in variable or []:
        args.extend(["--variable", entry])

    for entry in metadata or []:
        args.extend(["--metadata", entry])

    return args


def run_apply(
    input: str,
    output: str,
    template: str,
    *,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    variable: Optional[list[str]] = None,
    metadata: Optional[list[str]] = None,
) -> None:
    """Validate inputs, build the pandoc argv, run it, and report success.

    Raises ``typer.Exit(1)`` when the input file or the template file is
    missing. Emits a stderr warning (does NOT block) when the output
    extension is one pandoc ignores `--template` for (`.docx` / `.odt` /
    `.pptx`); pandoc itself returns success in that case so we don't want
    to fail the user's command.
    """
    input_path = Path(input)
    if not input_path.exists():
        typer.echo(f"ERROR: Input file not found: {input}", err=True)
        raise typer.Exit(code=1)

    template_path = Path(template)
    if not template_path.exists():
        typer.echo(f"ERROR: Template file not found: {template}", err=True)
        raise typer.Exit(code=1)

    output_suffix = Path(output).suffix.lower() if output != "-" else ""
    if output_suffix in _REFERENCE_DOC_SUFFIXES:
        if output_suffix == ".epub":
            hint = (
                "Use --css / --epub-stylesheet / --epub-cover-image for EPUB styling."
            )
        else:
            hint = "Use --reference-doc for DOCX/ODT/PPTX styling."
        typer.echo(
            f"WARNING: --template is silently ignored for {output_suffix} output. "
            + hint,
            err=True,
        )

    args = build_args(
        input,
        output,
        template,
        from_=from_,
        to=to,
        variable=variable,
        metadata=metadata,
    )

    run_pandoc(args, check=True, capture=True)

    if output != "-":
        report_success(output)
