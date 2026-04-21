"""Tier 2: slides integration tests against the real pandoc binary."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from typer.testing import CliRunner

from _pandoc_helpers import assert_html_doctype, assert_pdf_magic


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


@pytest.fixture(scope="module")
def app(pandoc_path: str):  # noqa: ARG001 - fixture forces a clean skip when pandoc is absent
    from pandoc_cli import app as typer_app

    return typer_app


@pytest.fixture
def repo_tmp_path() -> Path:
    root = Path(__file__).resolve().parents[2] / "tmp"
    root.mkdir(exist_ok=True)
    path = root / f"pandoc-slides-{uuid.uuid4().hex}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def slides_md(repo_tmp_path: Path) -> Path:
    path = repo_tmp_path / "slides.md"
    path.write_text(
        """\
# Heading One

This is the first paragraph with **bold** and *italic* text.

## Heading Two

A second-level section.

- Item one
- Item two
- Item three
""",
        encoding="utf-8",
    )
    return path


class TestSlidesRevealjs:
    def test_revealjs_html_output_is_valid(self, runner, app, slides_md, repo_tmp_path):
        out = repo_tmp_path / "deck.html"
        result = runner.invoke(
            app,
            [
                "slides",
                "build",
                str(slides_md),
                str(out),
                "--to",
                "revealjs",
                "--standalone",
                "--embed-resources",
            ],
        )

        combined = ((result.stdout or "") + (result.stderr or "") + (result.output or "")).lower()
        if result.exit_code != 0 and "no store" in combined:
            pytest.skip("Skipping: revealjs output is blocked by the local pandoc certificate store.")

        assert result.exit_code == 0, result.output
        assert_html_doctype(out)
        text = out.read_text(encoding="utf-8").lower()
        assert "reveal" in text
        assert "<section" in text


class TestSlidesBeamer:
    def test_beamer_pdf_output_is_valid(self, runner, app, slides_md, repo_tmp_path, latex_engine):
        out = repo_tmp_path / "deck.pdf"
        result = runner.invoke(
            app,
            [
                "slides",
                "build",
                str(slides_md),
                str(out),
                "--to",
                "beamer",
                "--pdf-engine",
                latex_engine,
                "--standalone",
            ],
        )

        combined = ((result.stdout or "") + (result.stderr or "") + (result.output or "")).lower()
        if result.exit_code != 0 and (
            "beamer.cls not found" in combined
            or "no store" in combined
            or "miktex\\log/pdflatex.log" in combined
        ):
            pytest.skip("Skipping: beamer PDF rendering is blocked by the local LaTeX installation.")

        assert result.exit_code == 0, result.output
        assert_pdf_magic(out)


class TestSlidesErrors:
    def test_revealjs_rejects_pdf_engine(self, runner, app, slides_md, repo_tmp_path):
        out = repo_tmp_path / "deck.html"
        result = runner.invoke(
            app,
            [
                "slides",
                "build",
                str(slides_md),
                str(out),
                "--to",
                "revealjs",
                "--pdf-engine",
                "xelatex",
            ],
        )

        assert result.exit_code == 1
        combined = (result.stderr or "") + (result.output or "")
        assert "--pdf-engine" in combined
        assert "beamer slide output" in combined
