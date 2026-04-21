"""pandoc CLI — universal document conversion."""

import typer

app = typer.Typer(
    name="pandoc-cli",
    help="Agent-native CLI for pandoc — convert, citations, templates, filters, info.",
    no_args_is_help=True,
)

# Sub-app per command group. Commands are registered onto these by the
# command-group modules below.
convert_app = typer.Typer(help="Convert between formats (md, pdf, docx, html, epub, latex)", no_args_is_help=True)
citations_app = typer.Typer(help="Render citations from BibTeX / CSL bibliographies", no_args_is_help=True)
templates_app = typer.Typer(help="Apply custom templates and bundled Eisvogel preset", no_args_is_help=True)
filters_app = typer.Typer(help="Apply Lua / JSON filters; pandoc-crossref helpers", no_args_is_help=True)
info_app = typer.Typer(help="Introspection: version, formats, PDF engines available", no_args_is_help=True)
slides_app = typer.Typer(help="Build slide decks with beamer or revealjs", no_args_is_help=True)

app.add_typer(convert_app, name="convert")
app.add_typer(citations_app, name="citations")
app.add_typer(templates_app, name="templates")
app.add_typer(filters_app, name="filters")
app.add_typer(info_app, name="info")
app.add_typer(slides_app, name="slides")

# Importing each module triggers its @sub_app.command() decorators.
import pandoc_cli.convert  # noqa: E402, F401
import pandoc_cli.citations  # noqa: E402, F401
import pandoc_cli.templates  # noqa: E402, F401
import pandoc_cli.filters  # noqa: E402, F401
import pandoc_cli.info  # noqa: E402, F401
import pandoc_cli.slides  # noqa: E402, F401
