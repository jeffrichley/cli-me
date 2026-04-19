"""Tier 1: convert command logic — mocked, no real pandoc binary needed.

Exercises `pandoc_cli.commands.convert_to.build_args` (pure) and
`run_convert` (impure, mocked). Asserts the constructed pandoc argv list
exactly, plus precondition behavior (missing input, no PDF engine).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import typer


# ---------------------------------------------------------------------------
# build_args — pure construction of the pandoc argv
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestBuildArgsBasics:
    def test_basic_input_output(self):
        from pandoc_cli.commands.convert_to import build_args

        assert build_args("doc.md", "doc.html") == ["doc.md", "-o", "doc.html"]

    def test_input_output_first_two_positions(self):
        """INPUT must always come before -o OUTPUT for pandoc to detect input
        format from extension."""
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "b.docx", toc=True)
        assert args[0] == "a.md"
        assert args[1] == "-o"
        assert args[2] == "b.docx"

    def test_paths_with_spaces_passed_through(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("My Doc.md", "Out Folder/Out.pdf")
        assert args[0] == "My Doc.md"
        assert "Out Folder/Out.pdf" in args


@pytest.mark.command_graph
class TestBuildArgsFormats:
    def test_from_format_added(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", from_="markdown+yaml_metadata_block")
        assert "--from" in args
        i = args.index("--from")
        assert args[i + 1] == "markdown+yaml_metadata_block"

    def test_to_format_added(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.out", to="html5")
        assert "--to" in args
        i = args.index("--to")
        assert args[i + 1] == "html5"

    def test_extension_string_not_split(self):
        """`markdown+smart-citations` is a single token; we must not split on
        + or -."""
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", from_="markdown+smart-citations")
        assert "markdown+smart-citations" in args
        # Verify nothing got split into separate "smart" or "citations" tokens.
        assert "smart" not in args
        assert "citations" not in args


@pytest.mark.command_graph
class TestBuildArgsStandalone:
    def test_standalone_true(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", standalone=True)
        assert "--standalone" in args
        assert "--standalone=false" not in args

    def test_standalone_false(self):
        """Pandoc's CLI uses ``--standalone=false`` (not ``--no-standalone``);
        verified against `pandoc --help` for pandoc 3.9.0.2."""
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", standalone=False)
        assert "--standalone=false" in args
        # Bare --standalone must NOT be present (and the legacy --no-standalone
        # must NOT be emitted — pandoc rejects it with "Unknown option").
        assert "--standalone" not in args
        assert "--no-standalone" not in args

    def test_standalone_none_emits_neither(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", standalone=None)
        assert "--standalone" not in args
        assert "--standalone=false" not in args
        assert "--no-standalone" not in args


@pytest.mark.command_graph
class TestBuildArgsToc:
    def test_toc_flag(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", toc=True)
        assert "--toc" in args

    def test_toc_off_by_default(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html")
        assert "--toc" not in args

    def test_toc_depth_added(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", toc=True, toc_depth=2)
        assert "--toc" in args
        assert "--toc-depth" in args
        i = args.index("--toc-depth")
        assert args[i + 1] == "2"

    def test_toc_depth_without_toc(self):
        """toc-depth alone is still forwarded — pandoc accepts it without --toc
        too (no-op then). Don't second-guess the user.

        Also assert `--toc` is genuinely absent so we catch any future regression
        that auto-adds it whenever toc_depth is passed.
        """
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", toc_depth=4)
        assert "--toc-depth" in args
        i = args.index("--toc-depth")
        assert args[i + 1] == "4"
        assert "--toc" not in args


@pytest.mark.command_graph
class TestBuildArgsMetadata:
    def test_single_metadata_pair(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", metadata=["title=Hello"])
        # Each entry must be preceded by --metadata.
        assert args.count("--metadata") == 1
        i = args.index("--metadata")
        assert args[i + 1] == "title=Hello"

    def test_multiple_metadata_pairs(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args(
            "a.md",
            "a.html",
            metadata=["title=Hello", "author=Jeff"],
        )
        assert args.count("--metadata") == 2
        # Both values should appear.
        assert "title=Hello" in args
        assert "author=Jeff" in args

    def test_empty_metadata_list(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", metadata=[])
        assert "--metadata" not in args

    def test_metadata_default_none(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html")
        assert "--metadata" not in args


@pytest.mark.command_graph
class TestBuildArgsPdfEngine:
    def test_pdf_engine_added(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.pdf", pdf_engine="xelatex")
        assert "--pdf-engine" in args
        i = args.index("--pdf-engine")
        assert args[i + 1] == "xelatex"

    def test_pdf_engine_omitted_by_default(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.pdf")
        assert "--pdf-engine" not in args


@pytest.mark.command_graph
class TestBuildArgsEmbedResources:
    def test_embed_resources_added(self):
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", embed_resources=True)
        assert "--embed-resources" in args

    def test_embed_resources_does_not_imply_standalone_explicitly(self):
        """Pandoc's --embed-resources implies --standalone for HTML; we don't
        want to double-flag, so build_args should NOT add --standalone unless
        the caller asked for it."""
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", embed_resources=True)
        assert "--embed-resources" in args
        assert "--standalone" not in args

    def test_embed_resources_with_explicit_standalone(self):
        """Caller can still pass standalone=True explicitly; both flags appear."""
        from pandoc_cli.commands.convert_to import build_args

        args = build_args("a.md", "a.html", embed_resources=True, standalone=True)
        assert "--embed-resources" in args
        assert "--standalone" in args


@pytest.mark.command_graph
class TestBuildArgsCombined:
    def test_full_invocation(self):
        """Exercise every option simultaneously and assert the EXACT argv list.

        Equality (not membership) catches duplication and pair-breaking
        mutations that ``flag in args`` misses (e.g. swapping flag order,
        dropping a value but keeping its flag, double-emitting --metadata).
        """
        from pandoc_cli.commands.convert_to import build_args

        args = build_args(
            "in.md",
            "out.pdf",
            from_="markdown",
            to="latex",
            standalone=True,
            toc=True,
            toc_depth=3,
            metadata=["title=T", "author=A"],
            pdf_engine="xelatex",
        )
        assert args == [
            "in.md",
            "-o",
            "out.pdf",
            "--from",
            "markdown",
            "--to",
            "latex",
            "--standalone",
            "--toc",
            "--toc-depth",
            "3",
            "--metadata",
            "title=T",
            "--metadata",
            "author=A",
            "--pdf-engine",
            "xelatex",
        ]


# ---------------------------------------------------------------------------
# run_convert — preconditions + delegation to backend.run_pandoc
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunConvertPreconditions:
    def test_missing_input_exits_one_before_calling_pandoc(self, tmp_path):
        from pandoc_cli.commands import convert_to

        bogus = tmp_path / "does_not_exist.md"
        out = tmp_path / "out.html"

        with patch.object(convert_to, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                convert_to.run_convert(str(bogus), str(out))
        assert exc.value.exit_code == 1
        mock_run.assert_not_called()

    def test_pdf_output_with_no_engine_exits_one(self, tmp_path):
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")
        out = tmp_path / "doc.pdf"

        with patch.object(convert_to, "find_pdf_engines", return_value=[]):
            with patch.object(convert_to, "run_pandoc") as mock_run:
                with pytest.raises(typer.Exit) as exc:
                    convert_to.run_convert(str(src), str(out))
        assert exc.value.exit_code == 1
        mock_run.assert_not_called()

    def test_pdf_output_with_engine_proceeds(self, tmp_path):
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")
        out = tmp_path / "doc.pdf"

        with patch.object(convert_to, "find_pdf_engines", return_value=["xelatex"]):
            with patch.object(convert_to, "run_pandoc") as mock_run:
                with patch.object(convert_to, "report_success"):
                    convert_to.run_convert(str(src), str(out), pdf_engine="xelatex")

        mock_run.assert_called_once()
        called_args = mock_run.call_args.args[0]
        assert called_args[0] == str(src)
        assert "-o" in called_args
        assert called_args[called_args.index("-o") + 1] == str(out)
        # Pair-tight check: --pdf-engine must be immediately followed by "xelatex".
        # A mutation that drops the engine value but keeps the flag would fail here.
        assert "--pdf-engine" in called_args
        assert called_args[called_args.index("--pdf-engine") + 1] == "xelatex"


@pytest.mark.command_graph
class TestRunConvertDelegation:
    def test_non_pdf_output_skips_engine_check(self, tmp_path):
        """HTML output must NOT trigger find_pdf_engines."""
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")
        out = tmp_path / "doc.html"

        with patch.object(convert_to, "find_pdf_engines") as mock_find:
            with patch.object(convert_to, "run_pandoc"):
                with patch.object(convert_to, "report_success"):
                    convert_to.run_convert(str(src), str(out))
        mock_find.assert_not_called()

    def test_forwards_options_into_argv(self, tmp_path):
        """Each flag must be immediately followed by its expected value.

        Pair-tight checks (``args[args.index(flag) + 1] == value``) catch
        mutations where the value is dropped but the flag is kept, or the
        wrong value is paired — both of which a bare ``in called_args`` test
        would silently accept.
        """
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")
        out = tmp_path / "doc.html"

        with patch.object(convert_to, "run_pandoc") as mock_run:
            with patch.object(convert_to, "report_success"):
                convert_to.run_convert(
                    str(src),
                    str(out),
                    from_="markdown",
                    to="html5",
                    standalone=True,
                    toc=True,
                    toc_depth=2,
                    metadata=["title=Hi"],
                )

        called_args = mock_run.call_args.args[0]
        assert called_args[called_args.index("--from") + 1] == "markdown"
        assert called_args[called_args.index("--to") + 1] == "html5"
        assert "--standalone" in called_args
        assert "--toc" in called_args
        assert called_args[called_args.index("--toc-depth") + 1] == "2"
        assert called_args[called_args.index("--metadata") + 1] == "title=Hi"

    def test_stdout_output_skips_report_success(self, tmp_path):
        """`output == '-'` means stdout; we should not echo a 'Wrote: -' line."""
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")

        with patch.object(convert_to, "run_pandoc"):
            with patch.object(convert_to, "report_success") as mock_report:
                convert_to.run_convert(str(src), "-")

        mock_report.assert_not_called()

    def test_file_output_calls_report_success(self, tmp_path):
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")
        out = tmp_path / "doc.html"

        with patch.object(convert_to, "run_pandoc"):
            with patch.object(convert_to, "report_success") as mock_report:
                convert_to.run_convert(str(src), str(out))

        mock_report.assert_called_once_with(str(out))

    def test_stdout_does_not_trigger_pdf_engine_check(self, tmp_path):
        """`-` is not a PDF path; engine check must be skipped."""
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")

        with patch.object(convert_to, "find_pdf_engines") as mock_find:
            with patch.object(convert_to, "run_pandoc"):
                convert_to.run_convert(str(src), "-")
        mock_find.assert_not_called()

    def test_stdout_output_forwards_pandoc_stdout(self, tmp_path, capsys):
        """When output is '-', pandoc's captured stdout must be re-emitted."""
        import subprocess
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")

        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="<h1>hi</h1>\n", stderr=""
        )
        with patch.object(convert_to, "run_pandoc", return_value=fake_result):
            convert_to.run_convert(str(src), "-")

        captured = capsys.readouterr()
        assert "<h1>hi</h1>" in captured.out


# ---------------------------------------------------------------------------
# New validations: binary-stdout refusal + explicit pdf-engine check
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunConvertBinaryStdout:
    def test_docx_to_stdout_refused(self, tmp_path, capsys):
        """`convert to in.md - --to docx` must exit 1 BEFORE invoking pandoc.

        Backend runs pandoc with text=True, so a binary writer to stdout would
        either crash with UnicodeDecodeError or silently corrupt bytes. Refuse
        upfront with a clear, actionable message.
        """
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")

        with patch.object(convert_to, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                convert_to.run_convert(str(src), "-", to="docx")
        assert exc.value.exit_code == 1
        mock_run.assert_not_called()
        captured = capsys.readouterr()
        # Message must name the format and point at the fix.
        assert "docx" in captured.err
        assert "stdout" in captured.err.lower()

    def test_pdf_to_stdout_refused(self, tmp_path):
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")

        with patch.object(convert_to, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                convert_to.run_convert(str(src), "-", to="pdf")
        assert exc.value.exit_code == 1
        mock_run.assert_not_called()

    def test_epub_to_stdout_refused(self, tmp_path):
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")

        with patch.object(convert_to, "run_pandoc") as mock_run:
            with pytest.raises(typer.Exit) as exc:
                convert_to.run_convert(str(src), "-", to="epub")
        assert exc.value.exit_code == 1
        mock_run.assert_not_called()

    def test_html_to_stdout_allowed(self, tmp_path):
        """Text formats to stdout are fine — must NOT be refused."""
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")

        with patch.object(convert_to, "run_pandoc") as mock_run:
            convert_to.run_convert(str(src), "-", to="html5")
        mock_run.assert_called_once()


@pytest.mark.command_graph
class TestRunConvertPdfEngineValidation:
    def test_explicit_bogus_pdf_engine_exits_one(self, tmp_path, capsys):
        """`--pdf-engine=BOGUS` must be rejected upfront when not on PATH."""
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")
        out = tmp_path / "doc.pdf"

        with patch.object(convert_to, "find_pdf_engines", return_value=["xelatex"]):
            with patch.object(convert_to, "run_pandoc") as mock_run:
                with pytest.raises(typer.Exit) as exc:
                    convert_to.run_convert(
                        str(src), str(out), pdf_engine="nonexistent.engine"
                    )
        assert exc.value.exit_code == 1
        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "nonexistent.engine" in captured.err
        assert "not found" in captured.err.lower()
        # Available engines must be surfaced so the user knows what to pick.
        assert "xelatex" in captured.err

    def test_explicit_valid_pdf_engine_proceeds(self, tmp_path):
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")
        out = tmp_path / "doc.pdf"

        with patch.object(convert_to, "find_pdf_engines", return_value=["xelatex", "pdflatex"]):
            with patch.object(convert_to, "run_pandoc") as mock_run:
                with patch.object(convert_to, "report_success"):
                    convert_to.run_convert(
                        str(src), str(out), pdf_engine="xelatex"
                    )
        mock_run.assert_called_once()

    def test_no_explicit_engine_skips_engine_name_check(self, tmp_path):
        """When --pdf-engine is omitted, we still require an engine on PATH
        (via the existing pdf_output check), but no per-name validation runs.

        This guards against accidentally adding an extra strict check on the
        omitted-engine path.
        """
        from pandoc_cli.commands import convert_to

        src = tmp_path / "doc.md"
        src.write_text("# hi\n")
        out = tmp_path / "doc.pdf"

        with patch.object(convert_to, "find_pdf_engines", return_value=["pdflatex"]):
            with patch.object(convert_to, "run_pandoc") as mock_run:
                with patch.object(convert_to, "report_success"):
                    convert_to.run_convert(str(src), str(out))
        mock_run.assert_called_once()
