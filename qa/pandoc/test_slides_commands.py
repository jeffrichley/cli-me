"""Tier 1: slides command registration and argv construction."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner


def test_slides_group_is_registered():
    from pandoc_cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["slides", "--help"])

    assert result.exit_code == 0, result.output
    text = (result.stdout or result.output).lower()
    assert "build" in text


@pytest.mark.command_graph
def test_build_args_revealjs_happy_path():
    from pandoc_cli.commands.slides_build import build_args

    assert build_args(
        "deck.md",
        "deck.html",
        to="revealjs",
        from_="markdown",
        slide_level=2,
        incremental=True,
        standalone=True,
        toc=True,
        metadata=["title=Deck"],
        variable=["theme=black"],
        embed_resources=True,
    ) == [
        "deck.md",
        "-o",
        "deck.html",
        "--to",
        "revealjs",
        "--from",
        "markdown",
        "--slide-level",
        "2",
        "--incremental",
        "--standalone",
        "--toc",
        "--metadata",
        "title=Deck",
        "--variable",
        "theme=black",
        "--embed-resources",
    ]


@pytest.mark.command_graph
def test_build_args_beamer_happy_path():
    from pandoc_cli.commands.slides_build import build_args

    assert build_args(
        "deck.md",
        "deck.pdf",
        to="beamer",
        pdf_engine="xelatex",
        variable=["theme:default"],
    ) == [
        "deck.md",
        "-o",
        "deck.pdf",
        "--to",
        "beamer",
        "--pdf-engine",
        "xelatex",
        "--variable",
        "theme:default",
    ]


@pytest.mark.command_graph
def test_build_args_no_standalone_emits_false_flag():
    from pandoc_cli.commands.slides_build import build_args

    assert build_args(
        "deck.md",
        "deck.html",
        to="revealjs",
        standalone=False,
    ) == [
        "deck.md",
        "-o",
        "deck.html",
        "--to",
        "revealjs",
        "--standalone=false",
    ]


@pytest.mark.command_graph
def test_slides_build_cli_dispatches_to_run_build():
    from pandoc_cli import app
    from pandoc_cli.commands import slides_build

    runner = CliRunner()
    with patch.object(slides_build, "run_build") as mock_run:
        result = runner.invoke(
            app,
            [
                "slides",
                "build",
                "deck.md",
                "deck.html",
                "--to",
                "revealjs",
                "--slide-level",
                "2",
                "--incremental",
                "--standalone",
                "--toc",
                "--metadata",
                "title=Deck",
                "--variable",
                "theme=black",
                "--embed-resources",
            ],
        )

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once_with(
        "deck.md",
        "deck.html",
        to="revealjs",
        from_=None,
        slide_level=2,
        incremental=True,
        standalone=True,
        toc=True,
        metadata=["title=Deck"],
        variable=["theme=black"],
        pdf_engine=None,
        embed_resources=True,
    )


@pytest.mark.command_graph
def test_slides_build_cli_dispatches_beamer_pdf_engine_and_no_standalone():
    from pandoc_cli import app
    from pandoc_cli.commands import slides_build

    runner = CliRunner()
    with patch.object(slides_build, "run_build") as mock_run:
        result = runner.invoke(
            app,
            [
                "slides",
                "build",
                "deck.md",
                "deck.pdf",
                "--to",
                "beamer",
                "--pdf-engine",
                "xelatex",
                "--no-standalone",
            ],
        )

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once_with(
        "deck.md",
        "deck.pdf",
        to="beamer",
        from_=None,
        slide_level=None,
        incremental=False,
        standalone=False,
        toc=False,
        metadata=[],
        variable=[],
        pdf_engine="xelatex",
        embed_resources=False,
    )


@pytest.mark.command_graph
def test_run_build_rejects_unknown_writer():
    from pandoc_cli.commands import slides_build

    with patch.object(slides_build.Path, "exists", return_value=True):
        with patch.object(slides_build, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                slides_build.run_build("deck.md", "deck.html", to="slidy")
        assert exc.value.exit_code == 1
        mock_run.assert_not_called()


@pytest.mark.command_graph
def test_run_build_rejects_missing_input():
    from pandoc_cli.commands import slides_build

    with patch.object(slides_build.Path, "exists", return_value=False):
        with patch.object(slides_build, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                slides_build.run_build("deck.md", "deck.html", to="revealjs")
        assert exc.value.exit_code == 1
        mock_run.assert_not_called()


@pytest.mark.command_graph
def test_run_build_rejects_beamer_embed_resources():
    from pandoc_cli.commands import slides_build

    with patch.object(slides_build.Path, "exists", return_value=True):
        with patch.object(slides_build, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit):
                slides_build.run_build("deck.md", "deck.pdf", to="beamer", embed_resources=True)
        mock_run.assert_not_called()


@pytest.mark.command_graph
def test_run_build_rejects_revealjs_pdf_engine():
    from pandoc_cli.commands import slides_build

    with patch.object(slides_build.Path, "exists", return_value=True):
        with patch.object(slides_build, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit):
                slides_build.run_build("deck.md", "deck.html", to="revealjs", pdf_engine="xelatex")
        mock_run.assert_not_called()


@pytest.mark.command_graph
def test_run_build_allows_revealjs_stdout():
    from pandoc_cli.commands import slides_build

    with patch.object(slides_build.Path, "exists", return_value=True):
        with patch.object(slides_build, "run_pandoc") as mock_run:
            slides_build.run_build("deck.md", "-", to="revealjs")
        mock_run.assert_called_once()


@pytest.mark.command_graph
def test_run_build_rejects_beamer_stdout():
    from pandoc_cli.commands import slides_build

    with patch.object(slides_build.Path, "exists", return_value=True):
        with patch.object(slides_build, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit):
                slides_build.run_build("deck.md", "-", to="beamer")
        mock_run.assert_not_called()


@pytest.mark.command_graph
def test_run_build_checks_pdf_engine_for_beamer_pdf():
    from pandoc_cli.commands import slides_build

    with patch.object(slides_build.Path, "exists", return_value=True):
        with patch.object(slides_build, "find_pdf_engines", return_value=["xelatex"]):
            with patch.object(slides_build, "run_pandoc") as mock_run:
                with patch.object(slides_build, "report_success"):
                    slides_build.run_build("deck.md", "deck.pdf", to="beamer", pdf_engine="xelatex")
        mock_run.assert_called_once()


@pytest.mark.command_graph
def test_run_build_rejects_explicit_missing_pdf_engine():
    from pandoc_cli.commands import slides_build

    with patch.object(slides_build.Path, "exists", return_value=True):
        with patch.object(slides_build, "find_pdf_engines", return_value=["xelatex"]):
            with patch.object(slides_build, "run_pandoc") as mock_run:
                with pytest.raises(typer.Exit) as exc:
                    slides_build.run_build("deck.md", "deck.pdf", to="beamer", pdf_engine="pdflatex")
        assert exc.value.exit_code == 1
        mock_run.assert_not_called()


@pytest.mark.command_graph
def test_run_build_rejects_beamer_pdf_when_no_pdf_engines_exist():
    from pandoc_cli.commands import slides_build

    with patch.object(slides_build.Path, "exists", return_value=True):
        with patch.object(slides_build, "find_pdf_engines", return_value=[]):
            with patch.object(slides_build, "run_pandoc") as mock_run:
                with pytest.raises(typer.Exit) as exc:
                    slides_build.run_build("deck.md", "deck.pdf", to="beamer")
        assert exc.value.exit_code == 1
        mock_run.assert_not_called()
