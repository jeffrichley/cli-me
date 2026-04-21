"""Tier 1: citations command logic tests — mock subprocess, no real pandoc.

These tests cover:
  * `build_args` — exact pandoc argv construction for `citations render`
  * `run_render` — input/bib precondition validation + happy-path dispatch

Real-binary behavior (rendered citation text, output magic, not-found
warnings) lives in `test_citations_integration.py`.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from pandoc_cli import app
from pandoc_cli.commands.citations_render import build_args, run_render


# ---------------------------------------------------------------------------
# build_args — pure argv construction
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestBuildArgs:
    def test_basic_invocation_includes_citeproc_and_bib(self):
        args = build_args("doc.md", "doc.html", "refs.bib")
        # Source + sink + citeproc + bib are required for any rendered cite.
        assert "doc.md" in args
        assert "-o" in args
        assert "doc.html" in args
        assert "--citeproc" in args
        assert "--bibliography" in args
        # bib value must follow the flag in the same position
        bib_idx = args.index("--bibliography")
        assert args[bib_idx + 1] == "refs.bib"

    def test_csl_passed_through(self):
        args = build_args("doc.md", "doc.html", "refs.bib", csl="apa.csl")
        assert "--csl" in args
        assert args[args.index("--csl") + 1] == "apa.csl"

    def test_no_csl_means_no_csl_flag(self):
        args = build_args("doc.md", "doc.html", "refs.bib")
        assert "--csl" not in args

    def test_from_and_to_flags(self):
        args = build_args(
            "doc.md", "doc.html", "refs.bib",
            from_="markdown",
            to="html5",
        )
        assert "--from" in args
        assert args[args.index("--from") + 1] == "markdown"
        assert "--to" in args
        assert args[args.index("--to") + 1] == "html5"

    def test_extension_syntax_passed_verbatim(self):
        # gotchas.md: extension syntax (`+ext-ext`) must not be split
        args = build_args(
            "doc.md", "doc.html", "refs.bib",
            from_="markdown+yaml_metadata_block-implicit_figures",
        )
        assert "markdown+yaml_metadata_block-implicit_figures" in args

    def test_standalone_true_emits_standalone(self):
        args = build_args("doc.md", "doc.html", "refs.bib", standalone=True)
        assert "--standalone" in args
        assert "--no-standalone" not in args

    def test_standalone_false_emits_no_standalone(self):
        args = build_args("doc.md", "doc.html", "refs.bib", standalone=False)
        assert "--no-standalone" in args
        assert "--standalone" not in args

    def test_standalone_none_emits_neither(self):
        args = build_args("doc.md", "doc.html", "refs.bib", standalone=None)
        assert "--standalone" not in args
        assert "--no-standalone" not in args

    def test_metadata_passthrough_single(self):
        args = build_args(
            "doc.md", "doc.html", "refs.bib",
            metadata=["title=Foo"],
        )
        assert "--metadata" in args
        assert args[args.index("--metadata") + 1] == "title=Foo"

    def test_metadata_passthrough_multiple(self):
        args = build_args(
            "doc.md", "doc.html", "refs.bib",
            metadata=["title=Foo", "author=Jeff"],
        )
        # Both metadata flags must appear, each followed by its value
        meta_idxs = [i for i, a in enumerate(args) if a == "--metadata"]
        assert len(meta_idxs) == 2
        values = {args[i + 1] for i in meta_idxs}
        assert values == {"title=Foo", "author=Jeff"}

    def test_input_appears_before_output_o(self):
        # Pandoc accepts INPUT then -o OUTPUT; keep that order so error
        # messages from pandoc are intelligible.
        args = build_args("doc.md", "doc.html", "refs.bib")
        assert args.index("doc.md") < args.index("-o")

    def test_natbib_and_biblatex_never_in_argv(self):
        # Design contract: this subcommand always uses --citeproc and never
        # emits raw natbib/biblatex markers. A regression that introduced
        # either flag would silently change the rendered output format.
        args = build_args(
            "doc.md", "doc.html", "refs.bib",
            csl="apa.csl",
            from_="markdown",
            to="html5",
            standalone=True,
            metadata=["title=Foo"],
        )
        assert "--natbib" not in args
        assert "--biblatex" not in args

    def test_all_parameters_combined_full_argv(self):
        # R4 §3c — exercise EVERY parameter at once and assert the exact
        # argv shape so regressions in flag ordering, escaping, or
        # duplication are caught.
        args = build_args(
            "doc.md",
            "out.html",
            "refs.bib",
            csl="apa.csl",
            from_="markdown+yaml_metadata_block",
            to="html5",
            standalone=True,
            metadata=["title=Foo", "author=Jeff"],
        )
        assert args == [
            "doc.md",
            "-o", "out.html",
            "--from", "markdown+yaml_metadata_block",
            "--to", "html5",
            "--standalone",
            "--bibliography", "refs.bib",
            "--csl", "apa.csl",
            "--metadata", "title=Foo",
            "--metadata", "author=Jeff",
            "--citeproc",
        ]


# ---------------------------------------------------------------------------
# run_render — preconditions + dispatch
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunRender:
    def test_input_missing_exits_one(self, tmp_path: Path):
        # Bib exists, input does not.
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{x, title={X}, year={2020}}\n")
        missing = tmp_path / "nope.md"
        out = tmp_path / "out.html"

        with patch("pandoc_cli.commands.citations_render.run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                run_render(str(missing), str(out), str(bib))
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()

    def test_bibliography_missing_exits_one(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        missing_bib = tmp_path / "nope.bib"
        out = tmp_path / "out.html"

        with patch("pandoc_cli.commands.citations_render.run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                run_render(str(inp), str(out), str(missing_bib))
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()

    def test_happy_path_invokes_run_pandoc_with_built_args(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{x, title={X}, year={2020}}\n")
        out = tmp_path / "out.html"

        fake_proc = MagicMock()
        fake_proc.returncode = 0
        fake_proc.stderr = ""
        with patch("pandoc_cli.commands.citations_render.run_pandoc", return_value=fake_proc) as mock_run:
            run_render(str(inp), str(out), str(bib))
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "--citeproc" in args
            assert "--bibliography" in args
            assert str(bib) in args
            assert str(inp) in args
            assert str(out) in args

    def test_csl_forwarded_through_run_render(self, tmp_path: Path):
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{x, title={X}, year={2020}}\n")
        csl = tmp_path / "style.csl"
        csl.write_text("<style/>\n")
        out = tmp_path / "out.html"

        fake_proc = MagicMock()
        fake_proc.returncode = 0
        fake_proc.stderr = ""
        with patch("pandoc_cli.commands.citations_render.run_pandoc", return_value=fake_proc) as mock_run:
            run_render(str(inp), str(out), str(bib), csl=str(csl))
            args = mock_run.call_args[0][0]
            assert "--csl" in args
            assert args[args.index("--csl") + 1] == str(csl)

    def test_missing_csl_exits_one_before_invoking_pandoc(self, tmp_path: Path):
        # R3 fix: pre-flight existence check for --csl matches the BIB
        # pattern. Without this, pandoc emits a 6-line Haskell traceback.
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{x, title={X}, year={2020}}\n")
        missing_csl = tmp_path / "nope.csl"
        out = tmp_path / "out.html"

        with patch("pandoc_cli.commands.citations_render.run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                run_render(
                    str(inp), str(out), str(bib),
                    csl=str(missing_csl),
                )
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()

    def test_enl_bibliography_exits_one_with_targeted_hint(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        # R3 nice-to-fix: detect EndNote .enl and emit a targeted hint
        # before invoking pandoc (which would emit an opaque parser error).
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        # An .enl file that *exists* (so the bib-not-found check passes)
        enl = tmp_path / "library.enl"
        enl.write_bytes(b"\x00\x01binary endnote contents\x00")
        out = tmp_path / "out.html"

        with patch("pandoc_cli.commands.citations_render.run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                run_render(str(inp), str(out), str(enl))
            assert exc.value.exit_code == 1
            mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert ".enl" in captured.err
        assert "EndNote" in captured.err

    def test_run_render_propagates_nonzero_exit_code(self, tmp_path: Path):
        # When pandoc returns a non-zero exit, the wrapper preserves it
        # rather than always raising exit 1.
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{x, title={X}, year={2020}}\n")
        out = tmp_path / "out.html"

        fake_proc = MagicMock()
        fake_proc.returncode = 43
        fake_proc.stderr = "pandoc: terrible failure\n"
        with patch(
            "pandoc_cli.commands.citations_render.run_pandoc",
            return_value=fake_proc,
        ):
            with pytest.raises(typer.Exit) as exc:
                run_render(str(inp), str(out), str(bib))
            assert exc.value.exit_code == 43


# ---------------------------------------------------------------------------
# CLI surface — Typer wiring sanity check (still mocked).
# Confirms the dispatch in citations.py registers `render` and forwards args.
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestCitationsRenderCLI:
    def test_render_command_registered(self):
        runner = CliRunner()
        result = runner.invoke(app, ["citations", "render", "--help"])
        assert result.exit_code == 0
        # Help text mentions the bibliography option
        assert "--bibliography" in result.output

    def test_render_missing_input_exits_one(self, tmp_path: Path):
        runner = CliRunner()
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{x, title={X}, year={2020}}\n")
        out = tmp_path / "out.html"
        with patch("pandoc_cli.commands.citations_render.run_pandoc") as mock_run:
            result = runner.invoke(
                app,
                [
                    "citations", "render",
                    str(tmp_path / "nope.md"),
                    str(out),
                    "--bibliography", str(bib),
            ],
        )
            assert result.exit_code == 1
            assert "input" in result.output.lower()
            mock_run.assert_not_called()

    def test_render_missing_bib_exits_one(self, tmp_path: Path):
        runner = CliRunner()
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        out = tmp_path / "out.html"
        with patch("pandoc_cli.commands.citations_render.run_pandoc") as mock_run:
            result = runner.invoke(
                app,
                [
                    "citations", "render",
                    str(inp),
                    str(out),
                    "--bibliography", str(tmp_path / "nope.bib"),
            ],
        )
            assert result.exit_code == 1
            assert "bibliography" in result.output.lower()
            mock_run.assert_not_called()

    def test_render_missing_csl_exits_one_at_cli(self, tmp_path: Path):
        # New R3 fix surfaced at the CLI surface: --csl pre-flight check
        # exits 1 with a clear message before invoking pandoc.
        runner = CliRunner()
        inp = tmp_path / "doc.md"
        inp.write_text("# Hi\n")
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{x, title={X}, year={2020}}\n")
        out = tmp_path / "out.html"
        with patch("pandoc_cli.commands.citations_render.run_pandoc") as mock_run:
            result = runner.invoke(
                app,
                [
                    "citations", "render",
                    str(inp),
                    str(out),
                    "--bibliography", str(bib),
                    "--csl", str(tmp_path / "missing.csl"),
            ],
        )
            assert result.exit_code == 1
            assert "csl" in result.output.lower()
            mock_run.assert_not_called()
