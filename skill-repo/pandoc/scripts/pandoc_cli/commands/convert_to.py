"""Logic for `convert to` — build a pandoc invocation and run it.

Split into `build_args` (pure: input/output/options -> argv list) and
`run_convert` (impure: validates preconditions and shells out via the backend).
The split lets Tier 1 tests assert the exact pandoc argv without invoking
pandoc, while Tier 2 tests exercise the real binary end-to-end.

Notes on flag semantics (mirrors basic-conversion.md):

- `standalone=True`/`False` => add `--standalone` / `--standalone=false`.
  Pandoc's CLI accepts the long-form ``--standalone[=true|false]`` syntax
  (verified against pandoc 3.9.0.2's `--help`); it does NOT recognize a
  ``--no-standalone`` flag. ``standalone=None`` (the default) emits neither
  flag — pandoc decides implicitly per output format (binary formats are
  always standalone).
- `embed_resources=True` adds `--embed-resources`. Per pandoc, this implies
  `--standalone` for HTML output, so we do NOT also add `--standalone` here
  to avoid double-flagging; callers that want to force standalone explicitly
  can still pass `standalone=True`.
- `--metadata key=value` is repeatable; each entry is forwarded verbatim,
  letting pandoc parse `key=value`.
- `from_` / `to` strings (e.g. `markdown+yaml_metadata_block`) are passed
  through verbatim; the extension toggle syntax (`+ext` / `-ext`) is pandoc's
  responsibility, not ours.

Note: ``backend.run_pandoc`` runs pandoc with ``text=True``, so binary output
to stdout is not supported — when `output == "-"` we refuse upfront for any
known binary format (pdf/docx/epub/odt/pptx) before invoking pandoc, both to
avoid silent corruption and to give the caller a clean exit-1 error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pandoc_cli.backend import find_pdf_engines, report_success, run_pandoc

# Output extensions that require a PDF engine. Anything else either has its
# own pandoc writer (html, docx, epub, latex, ...) or is a text format we let
# pandoc handle implicitly.
_PDF_SUFFIXES = {".pdf"}

# Output formats that produce binary data and therefore cannot be safely
# written to stdout under our text-mode subprocess pipe. Matched by file
# extension OR by `--to` value.
_BINARY_FORMATS = frozenset({"pdf", "docx", "epub", "epub2", "epub3", "odt", "pptx"})
_BINARY_SUFFIXES = frozenset({".pdf", ".docx", ".epub", ".odt", ".pptx"})


def _is_pdf_output(output: str) -> bool:
    """True when the destination is a PDF file (by extension)."""
    if output == "-":
        return False
    return Path(output).suffix.lower() in _PDF_SUFFIXES


def _binary_stdout_format(output: str, to: Optional[str]) -> Optional[str]:
    """If ``output`` is stdout AND the format is binary, return the format
    name. Otherwise return None.

    Detects via ``--to`` value first (authoritative), then falls back to the
    output file extension. When output is `-` and no `--to` is given, the
    format is unknown and we cannot refuse on this basis.
    """
    if output != "-":
        return None
    if to is not None:
        # pandoc accepts e.g. `epub3`, `pdf`, `docx`; normalize lower-case
        # and strip any extension-style suffix pandoc allows.
        token = to.lower().split("+", 1)[0].split("-", 1)[0]
        if token in _BINARY_FORMATS:
            return token
    return None


def build_args(
    input: str,
    output: str,
    *,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    standalone: Optional[bool] = None,
    toc: bool = False,
    toc_depth: Optional[int] = None,
    metadata: Optional[list[str]] = None,
    pdf_engine: Optional[str] = None,
    embed_resources: bool = False,
) -> list[str]:
    """Construct the pandoc argv list for a `convert to` invocation.

    Pure function: no filesystem checks, no subprocess calls. Tests assert
    against the returned list directly.
    """
    args: list[str] = [str(input), "-o", str(output)]

    if from_ is not None:
        args.extend(["--from", from_])
    if to is not None:
        args.extend(["--to", to])

    if standalone is True:
        args.append("--standalone")
    elif standalone is False:
        # Pandoc's CLI uses --standalone=false (not --no-standalone) per
        # `pandoc --help`. Verified against pandoc 3.9.0.2.
        args.append("--standalone=false")
    # standalone is None: emit neither flag; pandoc decides per format.

    if toc:
        args.append("--toc")
    if toc_depth is not None:
        args.extend(["--toc-depth", str(toc_depth)])

    for entry in metadata or []:
        args.extend(["--metadata", entry])

    if pdf_engine is not None:
        args.extend(["--pdf-engine", pdf_engine])

    if embed_resources:
        # Pandoc treats --embed-resources as implying --standalone for HTML;
        # we deliberately do NOT add --standalone here to avoid duplicating
        # flags. Callers can still pass standalone=True explicitly.
        args.append("--embed-resources")

    return args


def run_convert(
    input: str,
    output: str,
    *,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    standalone: Optional[bool] = None,
    toc: bool = False,
    toc_depth: Optional[int] = None,
    metadata: Optional[list[str]] = None,
    pdf_engine: Optional[str] = None,
    embed_resources: bool = False,
) -> None:
    """Validate inputs, build the pandoc argv, run it, and report success.

    Raises `typer.Exit(1)` when:
    - the input file is missing
    - PDF output is requested but no PDF engine is on PATH
    - `--pdf-engine=ENGINE` was given explicitly but ENGINE is not on PATH
    - the output is `-` (stdout) but the requested format is binary

    Any pandoc failure (non-zero exit) is surfaced by ``backend.run_pandoc``
    itself: pandoc's stderr is forwarded to our stderr verbatim, then
    ``typer.Exit(returncode)`` is raised — no Python traceback, no swallowed
    error message.
    """
    input_path = Path(input)
    if not input_path.exists():
        typer.echo(f"ERROR: Input file not found: {input}", err=True)
        raise typer.Exit(code=1)

    # Refuse binary-to-stdout BEFORE invoking pandoc. ``backend.run_pandoc``
    # runs with ``text=True``, so any binary writer (pdf/docx/epub/...) would
    # blow up with UnicodeDecodeError and silently corrupt the result.
    binary_fmt = _binary_stdout_format(output, to)
    if binary_fmt is not None:
        typer.echo(
            f"ERROR: Cannot write binary format ({binary_fmt}) to stdout. "
            "Use a file path.",
            err=True,
        )
        raise typer.Exit(code=1)

    # If the user explicitly named a PDF engine, validate it's installed
    # *before* pandoc tries to use it. Pandoc's own error for a missing
    # engine is buffered into the failed subprocess and lost; checking
    # upfront gives the agent an actionable message.
    if pdf_engine is not None:
        available = find_pdf_engines()
        if pdf_engine not in available:
            available_str = ", ".join(available) if available else "(none found)"
            typer.echo(
                f"ERROR: PDF engine '{pdf_engine}' not found on PATH. "
                f"Available: {available_str}",
                err=True,
            )
            raise typer.Exit(code=1)

    if _is_pdf_output(output):
        engines = find_pdf_engines()
        if not engines:
            typer.echo(
                "ERROR: PDF output requested but no PDF engine found on PATH.\n"
                "Install one of:\n"
                "  Windows: install MiKTeX (https://miktex.org/) — provides pdflatex/xelatex\n"
                "  macOS:   brew install --cask mactex     (or basictex for a smaller install)\n"
                "  Linux:   apt install texlive-xetex      (or your distro's TeX bundle)\n"
                "Alternatives: weasyprint, wkhtmltopdf, prince, tectonic, typst.\n"
                "Re-run with --pdf-engine=ENGINE once installed.",
                err=True,
            )
            raise typer.Exit(code=1)

    args = build_args(
        input,
        output,
        from_=from_,
        to=to,
        standalone=standalone,
        toc=toc,
        toc_depth=toc_depth,
        metadata=metadata,
        pdf_engine=pdf_engine,
        embed_resources=embed_resources,
    )

    result = run_pandoc(args, check=True, capture=True)

    if output == "-":
        # Pandoc wrote the converted document to its captured stdout; forward
        # it to ours so the user / CliRunner can see it. `nl=False` keeps the
        # output byte-exact (pandoc already emits a trailing newline if the
        # writer wants one).
        if result.stdout:
            typer.echo(result.stdout, nl=False)
    else:
        report_success(output)
