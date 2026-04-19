"""Tier 1: templates command logic tests — mock subprocess, no real pandoc.

These tests cover:
  * ``run_print`` — emits ``--print-default-template=FORMAT`` and returns
    pandoc's stdout verbatim; surfaces non-zero exits.
  * ``build_args`` / ``run_apply`` — argv construction and precondition
    validation for ``templates apply``.
  * ``build_args`` / ``run_eisvogel`` — argv construction and the
    bundled-template / engine-availability checks for ``templates eisvogel``.

Real-binary behavior (template content, PDF magic, real Eisvogel run) lives
in ``test_templates_integration.py``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from pandoc_cli import app
from pandoc_cli.commands import templates_apply, templates_eisvogel, templates_print


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


# ===========================================================================
# templates print
# ===========================================================================


@pytest.mark.command_graph
class TestRunPrint:
    def test_returns_pandoc_stdout_verbatim(self):
        canned = "\\documentclass{article}\n$body$\n"
        with patch.object(
            templates_print, "run_pandoc", return_value=_fake_completed(stdout=canned)
        ) as mock_run:
            result = templates_print.run_print("latex")

        assert result == canned
        mock_run.assert_called_once()

    def test_passes_print_default_template_flag(self):
        with patch.object(
            templates_print, "run_pandoc", return_value=_fake_completed(stdout="x")
        ) as mock_run:
            templates_print.run_print("html5")

        args = mock_run.call_args[0][0]
        assert "--print-default-template=html5" in args

    def test_unknown_format_propagates_non_zero_exit(self):
        # When pandoc rejects the format, run_pandoc(check=True) raises
        # CalledProcessError; run_print should let that bubble up so the
        # typer dispatch can convert it into a non-zero exit code.
        err = subprocess.CalledProcessError(
            returncode=43,
            cmd=["pandoc", "--print-default-template=notarealformat"],
            output="",
            stderr="pandoc: Unknown writer: notarealformat",
        )
        with patch.object(templates_print, "run_pandoc", side_effect=err):
            with pytest.raises(subprocess.CalledProcessError) as exc:
                templates_print.run_print("notarealformat")
            assert exc.value.returncode == 43


# ===========================================================================
# templates apply
# ===========================================================================


@pytest.mark.command_graph
class TestApplyBuildArgs:
    def test_basic_invocation_includes_input_output_template(self):
        args = templates_apply.build_args("d.md", "d.tex", "tpl.tex")
        # All three required args present
        assert "d.md" in args
        assert "-o" in args
        assert "d.tex" in args
        assert "--template" in args
        # Template value follows the flag
        assert args[args.index("--template") + 1] == "tpl.tex"

    def test_input_appears_before_output_o(self):
        args = templates_apply.build_args("d.md", "d.tex", "tpl.tex")
        assert args.index("d.md") < args.index("-o")

    def test_single_variable_passed_through(self):
        args = templates_apply.build_args(
            "d.md", "d.tex", "tpl.tex", variable=["title=Hi"]
        )
        assert "--variable" in args
        assert args[args.index("--variable") + 1] == "title=Hi"

    def test_multiple_variables_each_get_their_own_flag(self):
        args = templates_apply.build_args(
            "d.md",
            "d.tex",
            "tpl.tex",
            variable=["title=Hi", "author=Jeff", "lang=en"],
        )
        var_idxs = [i for i, a in enumerate(args) if a == "--variable"]
        assert len(var_idxs) == 3
        values = {args[i + 1] for i in var_idxs}
        assert values == {"title=Hi", "author=Jeff", "lang=en"}

    def test_metadata_passed_through_repeatable(self):
        args = templates_apply.build_args(
            "d.md",
            "d.tex",
            "tpl.tex",
            metadata=["title=Foo", "author=Jeff"],
        )
        meta_idxs = [i for i, a in enumerate(args) if a == "--metadata"]
        assert len(meta_idxs) == 2
        values = {args[i + 1] for i in meta_idxs}
        assert values == {"title=Foo", "author=Jeff"}

    def test_from_and_to_passed_through(self):
        args = templates_apply.build_args(
            "d.md", "d.tex", "tpl.tex", from_="markdown", to="latex"
        )
        assert args[args.index("--from") + 1] == "markdown"
        assert args[args.index("--to") + 1] == "latex"

    def test_extension_syntax_passed_verbatim(self):
        args = templates_apply.build_args(
            "d.md",
            "d.tex",
            "tpl.tex",
            from_="markdown+yaml_metadata_block-implicit_figures",
        )
        assert "markdown+yaml_metadata_block-implicit_figures" in args


@pytest.mark.command_graph
class TestRunApply:
    def test_input_missing_exits_one(self, tmp_path: Path):
        tpl = tmp_path / "tpl.tex"
        tpl.write_text("$body$\n")
        missing = tmp_path / "nope.md"
        out = tmp_path / "out.tex"

        with patch.object(templates_apply, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                templates_apply.run_apply(str(missing), str(out), str(tpl))
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()

    def test_template_missing_exits_one(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        missing_tpl = tmp_path / "nope.tex"
        out = tmp_path / "out.tex"

        with patch.object(templates_apply, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                templates_apply.run_apply(str(inp), str(out), str(missing_tpl))
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()

    def test_happy_path_invokes_run_pandoc_with_built_args(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        tpl = tmp_path / "tpl.tex"
        tpl.write_text("$body$\n")
        out = tmp_path / "out.tex"

        with patch.object(
            templates_apply, "run_pandoc", return_value=_fake_completed()
        ) as mock_run:
            templates_apply.run_apply(str(inp), str(out), str(tpl))

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert str(inp) in args
        assert str(out) in args
        assert "--template" in args
        assert str(tpl) in args

    @pytest.mark.parametrize("ext", [".docx", ".odt", ".pptx"])
    def test_warns_on_reference_doc_outputs_but_does_not_block(
        self, tmp_path: Path, ext: str
    ):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        tpl = tmp_path / "tpl.tex"
        tpl.write_text("$body$\n")
        out = tmp_path / f"out{ext}"

        warnings: list[tuple[tuple, dict]] = []

        def capture_echo(*args, **kwargs):
            warnings.append((args, kwargs))

        with patch.object(
            templates_apply, "run_pandoc", return_value=_fake_completed()
        ) as mock_run, patch.object(typer, "echo", side_effect=capture_echo):
            templates_apply.run_apply(str(inp), str(out), str(tpl))

        # Pandoc was still invoked (we didn't block).
        mock_run.assert_called_once()
        # At least one stderr warning fired mentioning --template.
        stderr_msgs = [
            args[0]
            for (args, kwargs) in warnings
            if kwargs.get("err") is True and args
        ]
        assert any("--template" in m for m in stderr_msgs), (
            f"Expected --template warning on {ext} output; got {stderr_msgs!r}"
        )

    def test_no_warning_on_text_output(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        tpl = tmp_path / "tpl.tex"
        tpl.write_text("$body$\n")
        out = tmp_path / "out.tex"

        warnings: list[tuple[tuple, dict]] = []

        def capture_echo(*args, **kwargs):
            warnings.append((args, kwargs))

        with patch.object(
            templates_apply, "run_pandoc", return_value=_fake_completed()
        ), patch.object(typer, "echo", side_effect=capture_echo):
            templates_apply.run_apply(str(inp), str(out), str(tpl))

        stderr_msgs = [
            args[0]
            for (args, kwargs) in warnings
            if kwargs.get("err") is True and args
        ]
        # No --template-specific warning for .tex output
        assert not any("--template is silently ignored" in m for m in stderr_msgs)


# ===========================================================================
# templates eisvogel
# ===========================================================================


@pytest.mark.command_graph
class TestEisvogelBuildArgs:
    def test_includes_template_path(self, tmp_path: Path):
        fake_template = tmp_path / "eisvogel.latex"
        fake_template.write_text("% fake\n")
        args = templates_eisvogel.build_args(
            "in.md",
            "out.pdf",
            str(fake_template),
            pdf_engine="xelatex",
        )
        assert "--template" in args
        assert args[args.index("--template") + 1] == str(fake_template)

    def test_includes_pdf_engine_in_args(self, tmp_path: Path):
        args = templates_eisvogel.build_args(
            "in.md", "out.pdf", "tpl.latex", pdf_engine="xelatex"
        )
        assert "--pdf-engine=xelatex" in args

    def test_pdf_engine_pdflatex_fallback(self, tmp_path: Path):
        args = templates_eisvogel.build_args(
            "in.md", "out.pdf", "tpl.latex", pdf_engine="pdflatex"
        )
        assert "--pdf-engine=pdflatex" in args

    def test_toc_flag_forwarded(self, tmp_path: Path):
        args = templates_eisvogel.build_args(
            "in.md", "out.pdf", "tpl.latex", pdf_engine="xelatex", toc=True
        )
        assert "--toc" in args

    def test_toc_default_omits_flag(self, tmp_path: Path):
        args = templates_eisvogel.build_args(
            "in.md", "out.pdf", "tpl.latex", pdf_engine="xelatex"
        )
        assert "--toc" not in args

    def test_variables_forwarded(self, tmp_path: Path):
        args = templates_eisvogel.build_args(
            "in.md",
            "out.pdf",
            "tpl.latex",
            pdf_engine="xelatex",
            variable=["titlepage=true", "titlepage-color=0F4C81"],
        )
        var_idxs = [i for i, a in enumerate(args) if a == "--variable"]
        assert len(var_idxs) == 2
        values = {args[i + 1] for i in var_idxs}
        assert values == {"titlepage=true", "titlepage-color=0F4C81"}


@pytest.mark.command_graph
class TestRunEisvogel:
    def test_input_missing_exits_one(self, tmp_path: Path):
        out = tmp_path / "out.pdf"
        with patch.object(templates_eisvogel, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                templates_eisvogel.run_eisvogel(
                    str(tmp_path / "nope.md"), str(out)
                )
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()

    def test_bundled_template_missing_exits_one(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        out = tmp_path / "out.pdf"
        bogus_path = tmp_path / "deleted-eisvogel.latex"  # does NOT exist

        with patch.object(
            templates_eisvogel, "bundled_template_path", return_value=bogus_path
        ), patch.object(templates_eisvogel, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                templates_eisvogel.run_eisvogel(str(inp), str(out))
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()

    def test_no_pdf_engine_on_path_exits_one(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        fake_tpl = tmp_path / "eisvogel.latex"
        fake_tpl.write_text("% fake\n")
        out = tmp_path / "out.pdf"

        captured: list[str] = []

        def capture_echo(*args, **kwargs):
            if args and kwargs.get("err") is True:
                captured.append(str(args[0]))

        with patch.object(
            templates_eisvogel, "bundled_template_path", return_value=fake_tpl
        ), patch.object(
            templates_eisvogel, "find_pdf_engines", return_value=[]
        ), patch.object(templates_eisvogel, "run_pandoc") as mock_run, patch.object(
            typer, "echo", side_effect=capture_echo
        ):
            with pytest.raises(typer.Exit) as exc:
                templates_eisvogel.run_eisvogel(str(inp), str(out))
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()

        # Helpful message must mention installation guidance.
        joined = "\n".join(captured).lower()
        assert "install" in joined
        assert "miktex" in joined or "texlive" in joined or "mactex" in joined

    def test_picks_xelatex_when_available(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        fake_tpl = tmp_path / "eisvogel.latex"
        fake_tpl.write_text("% fake\n")
        out = tmp_path / "out.pdf"

        with patch.object(
            templates_eisvogel, "bundled_template_path", return_value=fake_tpl
        ), patch.object(
            templates_eisvogel,
            "find_pdf_engines",
            return_value=["pdflatex", "xelatex", "lualatex"],
        ), patch.object(
            templates_eisvogel, "run_pandoc", return_value=_fake_completed()
        ) as mock_run:
            templates_eisvogel.run_eisvogel(str(inp), str(out))

        args = mock_run.call_args[0][0]
        assert "--pdf-engine=xelatex" in args

    def test_falls_back_to_pdflatex_when_no_xelatex(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        fake_tpl = tmp_path / "eisvogel.latex"
        fake_tpl.write_text("% fake\n")
        out = tmp_path / "out.pdf"

        with patch.object(
            templates_eisvogel, "bundled_template_path", return_value=fake_tpl
        ), patch.object(
            templates_eisvogel,
            "find_pdf_engines",
            return_value=["pdflatex", "lualatex"],
        ), patch.object(
            templates_eisvogel, "run_pandoc", return_value=_fake_completed()
        ) as mock_run:
            templates_eisvogel.run_eisvogel(str(inp), str(out))

        args = mock_run.call_args[0][0]
        assert "--pdf-engine=pdflatex" in args

    def test_explicit_pdf_engine_overrides_default(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        fake_tpl = tmp_path / "eisvogel.latex"
        fake_tpl.write_text("% fake\n")
        out = tmp_path / "out.pdf"

        with patch.object(
            templates_eisvogel, "bundled_template_path", return_value=fake_tpl
        ), patch.object(
            templates_eisvogel,
            "find_pdf_engines",
            # find_pdf_engines should NOT be consulted when user passes --pdf-engine
            return_value=[],
        ), patch.object(
            templates_eisvogel, "run_pandoc", return_value=_fake_completed()
        ) as mock_run:
            templates_eisvogel.run_eisvogel(
                str(inp), str(out), pdf_engine="lualatex"
            )

        args = mock_run.call_args[0][0]
        assert "--pdf-engine=lualatex" in args

    def test_warns_when_output_not_pdf_extension(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        fake_tpl = tmp_path / "eisvogel.latex"
        fake_tpl.write_text("% fake\n")
        out = tmp_path / "out.html"

        captured: list[str] = []

        def capture_echo(*args, **kwargs):
            if args and kwargs.get("err") is True:
                captured.append(str(args[0]))

        with patch.object(
            templates_eisvogel, "bundled_template_path", return_value=fake_tpl
        ), patch.object(
            templates_eisvogel, "find_pdf_engines", return_value=["xelatex"]
        ), patch.object(
            templates_eisvogel, "run_pandoc", return_value=_fake_completed()
        ) as mock_run, patch.object(
            typer, "echo", side_effect=capture_echo
        ):
            templates_eisvogel.run_eisvogel(str(inp), str(out))

        # Warning was emitted but pandoc was still invoked.
        mock_run.assert_called_once()
        joined = "\n".join(captured).lower()
        assert "pdf" in joined and (".html" in joined or "warning" in joined)

    def test_toc_and_variables_forwarded(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        fake_tpl = tmp_path / "eisvogel.latex"
        fake_tpl.write_text("% fake\n")
        out = tmp_path / "out.pdf"

        with patch.object(
            templates_eisvogel, "bundled_template_path", return_value=fake_tpl
        ), patch.object(
            templates_eisvogel, "find_pdf_engines", return_value=["xelatex"]
        ), patch.object(
            templates_eisvogel, "run_pandoc", return_value=_fake_completed()
        ) as mock_run:
            templates_eisvogel.run_eisvogel(
                str(inp),
                str(out),
                toc=True,
                variable=["titlepage=true", "titlepage-color=0F4C81"],
            )

        args = mock_run.call_args[0][0]
        assert "--toc" in args
        var_idxs = [i for i, a in enumerate(args) if a == "--variable"]
        assert len(var_idxs) == 2


# ===========================================================================
# CLI surface — Typer wiring sanity check (still mocked).
# ===========================================================================


@pytest.mark.command_graph
class TestTemplatesCLI:
    def test_print_command_registered(self):
        runner = CliRunner()
        result = runner.invoke(app, ["templates", "print", "--help"])
        assert result.exit_code == 0
        assert "FORMAT" in result.output.upper()

    def test_apply_command_registered(self):
        runner = CliRunner()
        result = runner.invoke(app, ["templates", "apply", "--help"])
        assert result.exit_code == 0
        assert "--template" in result.output

    def test_eisvogel_command_registered(self):
        runner = CliRunner()
        result = runner.invoke(app, ["templates", "eisvogel", "--help"])
        assert result.exit_code == 0
        assert "--toc" in result.output

    def test_apply_missing_input_exits_one(self, tmp_path: Path):
        runner = CliRunner()
        tpl = tmp_path / "tpl.tex"
        tpl.write_text("$body$\n")
        out = tmp_path / "out.tex"
        with patch("pandoc_cli.commands.templates_apply.run_pandoc") as mock_run:
            result = runner.invoke(
                app,
                [
                    "templates",
                    "apply",
                    str(tmp_path / "nope.md"),
                    str(out),
                    "--template",
                    str(tpl),
                ],
            )
            assert result.exit_code == 1
            mock_run.assert_not_called()

    def test_apply_missing_template_exits_one(self, tmp_path: Path):
        runner = CliRunner()
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        out = tmp_path / "out.tex"
        with patch("pandoc_cli.commands.templates_apply.run_pandoc") as mock_run:
            result = runner.invoke(
                app,
                [
                    "templates",
                    "apply",
                    str(inp),
                    str(out),
                    "--template",
                    str(tmp_path / "nope.tex"),
                ],
            )
            assert result.exit_code == 1
            mock_run.assert_not_called()


# ===========================================================================
# R3 / R4 follow-up tests — engine validation, suffix stripping, EPUB warn,
# kitchen-sink argv assertions, packaging tripwire, resolver wiring.
# ===========================================================================


@pytest.mark.command_graph
class TestPrintExtensionStripping:
    """``templates print`` must handle ``+ext``/``-ext`` suffixed format names.

    Pandoc's ``--print-default-template`` rejects suffixed specs; the wrapper
    strips them and notes the change on stderr. See ``run_print`` docstring
    for the rationale.
    """

    def test_strips_plus_extension_before_forwarding(self):
        with patch.object(
            templates_print, "run_pandoc", return_value=_fake_completed(stdout="x")
        ) as mock_run:
            templates_print.run_print("markdown+smart")
        args = mock_run.call_args[0][0]
        # Bare format forwarded; suffix never reaches pandoc.
        assert "--print-default-template=markdown" in args
        assert "--print-default-template=markdown+smart" not in args

    def test_strips_minus_extension_before_forwarding(self):
        with patch.object(
            templates_print, "run_pandoc", return_value=_fake_completed(stdout="x")
        ) as mock_run:
            templates_print.run_print("markdown-implicit_figures")
        args = mock_run.call_args[0][0]
        assert "--print-default-template=markdown" in args

    def test_strips_compound_extension_chain(self):
        with patch.object(
            templates_print, "run_pandoc", return_value=_fake_completed(stdout="x")
        ) as mock_run:
            templates_print.run_print("markdown+yaml_metadata_block-implicit_figures")
        args = mock_run.call_args[0][0]
        assert "--print-default-template=markdown" in args

    def test_bare_format_unchanged(self):
        with patch.object(
            templates_print, "run_pandoc", return_value=_fake_completed(stdout="x")
        ) as mock_run:
            templates_print.run_print("latex")
        args = mock_run.call_args[0][0]
        assert "--print-default-template=latex" in args

    def test_strip_emits_stderr_note(self):
        captured: list[str] = []

        def capture_echo(*args, **kwargs):
            if args and kwargs.get("err") is True:
                captured.append(str(args[0]))

        with patch.object(
            templates_print, "run_pandoc", return_value=_fake_completed(stdout="x")
        ), patch.object(typer, "echo", side_effect=capture_echo):
            templates_print.run_print("markdown+smart")

        joined = "\n".join(captured).lower()
        assert "markdown+smart" in joined and "markdown" in joined

    def test_bare_format_emits_no_strip_note(self):
        captured: list[str] = []

        def capture_echo(*args, **kwargs):
            if args and kwargs.get("err") is True:
                captured.append(str(args[0]))

        with patch.object(
            templates_print, "run_pandoc", return_value=_fake_completed(stdout="x")
        ), patch.object(typer, "echo", side_effect=capture_echo):
            templates_print.run_print("latex")

        joined = "\n".join(captured).lower()
        assert "stripped" not in joined


@pytest.mark.command_graph
class TestApplyEpubWarning:
    """R3#3: ``.epub`` outputs must warn that ``--template`` is ignored."""

    def test_epub_output_warns_template_silently_ignored(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        tpl = tmp_path / "tpl.tex"
        tpl.write_text("$body$\n")
        out = tmp_path / "out.epub"

        captured: list[str] = []

        def capture_echo(*args, **kwargs):
            if args and kwargs.get("err") is True:
                captured.append(str(args[0]))

        with patch.object(
            templates_apply, "run_pandoc", return_value=_fake_completed()
        ) as mock_run, patch.object(typer, "echo", side_effect=capture_echo):
            templates_apply.run_apply(str(inp), str(out), str(tpl))

        # We warn but still invoke pandoc (matches DOCX/ODT/PPTX behavior).
        mock_run.assert_called_once()
        joined = "\n".join(captured).lower()
        assert ".epub" in joined and "--template" in joined

    def test_epub_warning_mentions_epub_styling_alternative(self, tmp_path: Path):
        """Hint text should point users at EPUB-specific styling flags."""
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        tpl = tmp_path / "tpl.tex"
        tpl.write_text("$body$\n")
        out = tmp_path / "out.epub"

        captured: list[str] = []

        def capture_echo(*args, **kwargs):
            if args and kwargs.get("err") is True:
                captured.append(str(args[0]))

        with patch.object(
            templates_apply, "run_pandoc", return_value=_fake_completed()
        ), patch.object(typer, "echo", side_effect=capture_echo):
            templates_apply.run_apply(str(inp), str(out), str(tpl))

        joined = "\n".join(captured).lower()
        # Anything pointing the user at EPUB styling — current message uses
        # --css / --epub-stylesheet.
        assert "--css" in joined or "--epub-stylesheet" in joined


@pytest.mark.command_graph
class TestEisvogelEngineValidation:
    """R3#4: explicit non-LaTeX ``--pdf-engine`` must be rejected upfront."""

    @pytest.mark.parametrize(
        "engine",
        ["weasyprint", "wkhtmltopdf", "prince", "pagedjs-cli", "typst", "groff", "pdfroff"],
    )
    def test_non_latex_pdf_engine_rejected(self, tmp_path: Path, engine: str):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        fake_tpl = tmp_path / "eisvogel.latex"
        fake_tpl.write_text("% fake\n")
        out = tmp_path / "out.pdf"

        captured: list[str] = []

        def capture_echo(*args, **kwargs):
            if args and kwargs.get("err") is True:
                captured.append(str(args[0]))

        with patch.object(
            templates_eisvogel, "bundled_template_path", return_value=fake_tpl
        ), patch.object(
            templates_eisvogel, "run_pandoc"
        ) as mock_run, patch.object(typer, "echo", side_effect=capture_echo):
            with pytest.raises(typer.Exit) as exc:
                templates_eisvogel.run_eisvogel(
                    str(inp), str(out), pdf_engine=engine
                )
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()

        joined = "\n".join(captured).lower()
        assert engine in joined
        assert "latex" in joined  # message mentions Eisvogel is a LaTeX template

    @pytest.mark.parametrize(
        "engine",
        ["pdflatex", "xelatex", "lualatex", "tectonic", "latexmk"],
    )
    def test_latex_engines_accepted(self, tmp_path: Path, engine: str):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        fake_tpl = tmp_path / "eisvogel.latex"
        fake_tpl.write_text("% fake\n")
        out = tmp_path / "out.pdf"

        with patch.object(
            templates_eisvogel, "bundled_template_path", return_value=fake_tpl
        ), patch.object(
            templates_eisvogel, "run_pandoc", return_value=_fake_completed()
        ) as mock_run:
            templates_eisvogel.run_eisvogel(
                str(inp), str(out), pdf_engine=engine
            )

        args = mock_run.call_args[0][0]
        assert f"--pdf-engine={engine}" in args


@pytest.mark.command_graph
class TestEisvogelStdoutOutput:
    """Eisvogel cannot stream a binary PDF to stdout; refuse OUTPUT == '-'."""

    def test_dash_output_rejected_with_helpful_message(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")

        captured: list[str] = []

        def capture_echo(*args, **kwargs):
            if args and kwargs.get("err") is True:
                captured.append(str(args[0]))

        with patch.object(
            templates_eisvogel, "run_pandoc"
        ) as mock_run, patch.object(typer, "echo", side_effect=capture_echo):
            with pytest.raises(typer.Exit) as exc:
                templates_eisvogel.run_eisvogel(str(inp), "-")
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()

        joined = "\n".join(captured).lower()
        assert "stdout" in joined or "binary" in joined or "'-'" in joined


@pytest.mark.command_graph
class TestEisvogelTemplateResolverWiring:
    """R4#3 + R4#4: prove the wrapper actually consults
    ``bundled_template_path('eisvogel.latex')`` and forwards its return
    value into ``--template`` argv. Catches the "ignore resolver / hardcode"
    mutation that no other test would catch.
    """

    def test_template_argv_equals_resolver_return_value(self, tmp_path: Path):
        # Distinct sentinel path so a hardcoded fallback wouldn't match.
        sentinel = tmp_path / "sentinel-eisvogel.latex"
        sentinel.write_text("% sentinel\n")
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        out = tmp_path / "out.pdf"

        with patch.object(
            templates_eisvogel, "bundled_template_path", return_value=sentinel
        ) as mock_resolver, patch.object(
            templates_eisvogel, "find_pdf_engines", return_value=["xelatex"]
        ), patch.object(
            templates_eisvogel, "run_pandoc", return_value=_fake_completed()
        ) as mock_run:
            templates_eisvogel.run_eisvogel(str(inp), str(out))

        # Resolver was consulted with the expected template name.
        mock_resolver.assert_called_with("eisvogel.latex")
        # Resolver's return value flows verbatim into --template argv.
        args = mock_run.call_args[0][0]
        assert "--template" in args
        assert args[args.index("--template") + 1] == str(sentinel)

    def test_bundled_eisvogel_template_exists_on_install(self):
        """Packaging tripwire: the bundled Eisvogel template must ship with
        the installed skill. If somebody deletes ``scripts/templates/
        eisvogel.latex`` (or renames it) this fails immediately, not at the
        next real Eisvogel run (which often skips environmentally).
        """
        from pandoc_cli.backend import bundled_template_path

        path = bundled_template_path("eisvogel.latex")
        assert path.exists(), (
            f"Bundled Eisvogel template missing: {path}. "
            "Did scripts/templates/eisvogel.latex get deleted?"
        )
        # Sanity: it's a non-trivial file (eisvogel.latex is ~30KB).
        assert path.stat().st_size > 10_000, (
            f"Bundled Eisvogel template suspiciously small: {path.stat().st_size} bytes"
        )


@pytest.mark.command_graph
class TestKitchenSinkArgs:
    """R4#5: full-coverage argv assertions for both ``apply.build_args`` and
    ``eisvogel.build_args``. Asserts exact argv ordering / content so any
    silent flag drop or duplication is caught.
    """

    def test_apply_kitchen_sink_argv_exact(self):
        args = templates_apply.build_args(
            "in.md",
            "out.tex",
            "tpl.tex",
            from_="markdown+yaml_metadata_block",
            to="latex",
            variable=["title=Hi", "author=Jeff"],
            metadata=["lang=en", "date=2026-04-18"],
        )
        # Positional input + -o + --template come first (order matters for
        # build_args; it's the documented contract).
        assert args[0] == "in.md"
        assert args[1] == "-o"
        assert args[2] == "out.tex"
        assert args[3] == "--template"
        assert args[4] == "tpl.tex"
        # --from / --to follow.
        assert "--from" in args
        assert args[args.index("--from") + 1] == "markdown+yaml_metadata_block"
        assert "--to" in args
        assert args[args.index("--to") + 1] == "latex"
        # Each --variable / --metadata appears exactly twice with the right
        # values in order.
        var_pairs = [
            (args[i], args[i + 1])
            for i, a in enumerate(args)
            if a == "--variable"
        ]
        assert var_pairs == [("--variable", "title=Hi"), ("--variable", "author=Jeff")]
        meta_pairs = [
            (args[i], args[i + 1])
            for i, a in enumerate(args)
            if a == "--metadata"
        ]
        assert meta_pairs == [
            ("--metadata", "lang=en"),
            ("--metadata", "date=2026-04-18"),
        ]
        # No flag was duplicated unexpectedly.
        assert args.count("--template") == 1
        assert args.count("-o") == 1

    def test_eisvogel_kitchen_sink_argv_exact(self):
        args = templates_eisvogel.build_args(
            "in.md",
            "out.pdf",
            "tpl.latex",
            pdf_engine="xelatex",
            toc=True,
            variable=["titlepage=true", "titlepage-color=0F4C81"],
        )
        # Positional input + -o + --template + --pdf-engine first.
        assert args[0] == "in.md"
        assert args[1] == "-o"
        assert args[2] == "out.pdf"
        assert args[3] == "--template"
        assert args[4] == "tpl.latex"
        assert args[5] == "--pdf-engine=xelatex"
        # --toc appears exactly once after the engine flag.
        assert args.count("--toc") == 1
        # Variables forwarded verbatim and in order.
        var_pairs = [
            (args[i], args[i + 1])
            for i, a in enumerate(args)
            if a == "--variable"
        ]
        assert var_pairs == [
            ("--variable", "titlepage=true"),
            ("--variable", "titlepage-color=0F4C81"),
        ]
        # No accidental duplicates.
        assert args.count("--pdf-engine=xelatex") == 1
        assert args.count("--template") == 1


@pytest.mark.command_graph
class TestRunApplyDashOutput:
    """R4 nice-to-fix: ``run_apply`` with ``output='-'`` should still invoke
    pandoc but not call ``report_success`` (no file to size).
    """

    def test_dash_output_invokes_pandoc_and_skips_report(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        tpl = tmp_path / "tpl.tex"
        tpl.write_text("$body$\n")

        with patch.object(
            templates_apply, "run_pandoc", return_value=_fake_completed()
        ) as mock_run, patch.object(
            templates_apply, "report_success"
        ) as mock_report:
            templates_apply.run_apply(str(inp), "-", str(tpl))

        mock_run.assert_called_once()
        mock_report.assert_not_called()
        # Output forwarded as "-" verbatim.
        args = mock_run.call_args[0][0]
        assert "-" in args
        assert args[args.index("-o") + 1] == "-"

    def test_dash_output_does_not_trip_reference_doc_warning(self, tmp_path: Path):
        """No suffix → no DOCX/EPUB warning, even though ``-`` has no ext."""
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        tpl = tmp_path / "tpl.tex"
        tpl.write_text("$body$\n")

        captured: list[str] = []

        def capture_echo(*args, **kwargs):
            if args and kwargs.get("err") is True:
                captured.append(str(args[0]))

        with patch.object(
            templates_apply, "run_pandoc", return_value=_fake_completed()
        ), patch.object(typer, "echo", side_effect=capture_echo):
            templates_apply.run_apply(str(inp), "-", str(tpl))

        joined = "\n".join(captured).lower()
        assert "silently ignored" not in joined
