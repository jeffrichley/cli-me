"""Tier 1: info command logic tests — mocked, no real pandoc binary needed.

These tests exercise the `run_*` functions in `pandoc_cli.commands.info_*`
directly, mocking the backend / subprocess / shutil layer so the test suite
runs deterministically with no dependency on a working pandoc install.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# run_version
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunVersion:
    def test_returns_detect_version_result(self):
        from pandoc_cli.commands import info_version

        with patch.object(info_version, "detect_version", return_value="3.9.0.2"):
            assert info_version.run_version() == "3.9.0.2"


@pytest.mark.command_graph
class TestDetectVersionParsing:
    """Direct tests for `backend.detect_version` parsing logic.

    Mocks `subprocess.run` so the test is hermetic. Without these, a regression
    that returned `parts[0]` ("pandoc") or `parts[2]` (Lua version line) would
    only be caught by the integration suite — and that suite skips when pandoc
    isn't installed. Tests use `cache_clear()` because `detect_version` is
    `lru_cache`d.
    """

    def setup_method(self):
        from pandoc_cli import backend

        backend.detect_version.cache_clear()

    def teardown_method(self):
        from pandoc_cli import backend

        backend.detect_version.cache_clear()

    def test_parses_version_from_pandoc_output(self):
        from pandoc_cli import backend

        fake = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="pandoc 3.9.0.2\nFeatures: +server +lua\nScripting engine: Lua 5.4\n",
            stderr="",
        )
        with (
            patch.object(backend, "find_pandoc", return_value="/fake/pandoc"),
            patch.object(backend.subprocess, "run", return_value=fake),
        ):
            assert backend.detect_version() == "3.9.0.2"

    def test_returns_unknown_for_empty_stdout(self):
        from pandoc_cli import backend

        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        with (
            patch.object(backend, "find_pandoc", return_value="/fake/pandoc"),
            patch.object(backend.subprocess, "run", return_value=fake),
        ):
            assert backend.detect_version() == "unknown"

    def test_returns_unknown_when_first_word_is_not_pandoc(self):
        from pandoc_cli import backend

        fake = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="bogus 1.2.3\nFeatures: nothing\n",
            stderr="",
        )
        with (
            patch.object(backend, "find_pandoc", return_value="/fake/pandoc"),
            patch.object(backend.subprocess, "run", return_value=fake),
        ):
            assert backend.detect_version() == "unknown"

    def test_returns_unknown_when_only_one_word(self):
        from pandoc_cli import backend

        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="pandoc\n", stderr=""
        )
        with (
            patch.object(backend, "find_pandoc", return_value="/fake/pandoc"),
            patch.object(backend.subprocess, "run", return_value=fake),
        ):
            assert backend.detect_version() == "unknown"


# ---------------------------------------------------------------------------
# run_formats
# ---------------------------------------------------------------------------


def _fake_completed(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


@pytest.mark.command_graph
class TestRunFormats:
    def test_both_returns_both_lists(self):
        from pandoc_cli.commands import info_formats

        def fake_run_pandoc(args, *, check=True, capture=True):
            if "--list-input-formats" in args:
                return _fake_completed("markdown\nhtml\nlatex\n")
            if "--list-output-formats" in args:
                return _fake_completed("html\ndocx\npdf\nlatex\n")
            raise AssertionError(f"Unexpected pandoc args: {args}")

        with patch.object(info_formats, "run_pandoc", side_effect=fake_run_pandoc):
            result = info_formats.run_formats(side="both")

        assert result == {
            "input": ["markdown", "html", "latex"],
            "output": ["html", "docx", "pdf", "latex"],
        }

    def test_input_only_returns_input_list_and_empty_output(self):
        from pandoc_cli.commands import info_formats

        calls = []

        def fake_run_pandoc(args, *, check=True, capture=True):
            calls.append(args)
            assert "--list-input-formats" in args
            assert "--list-output-formats" not in args
            return _fake_completed("markdown\nhtml\n")

        with patch.object(info_formats, "run_pandoc", side_effect=fake_run_pandoc):
            result = info_formats.run_formats(side="input")

        assert result == {"input": ["markdown", "html"], "output": []}
        assert len(calls) == 1

    def test_output_only_returns_output_list_and_empty_input(self):
        from pandoc_cli.commands import info_formats

        calls = []

        def fake_run_pandoc(args, *, check=True, capture=True):
            calls.append(args)
            assert "--list-output-formats" in args
            assert "--list-input-formats" not in args
            return _fake_completed("docx\npdf\n")

        with patch.object(info_formats, "run_pandoc", side_effect=fake_run_pandoc):
            result = info_formats.run_formats(side="output")

        assert result == {"input": [], "output": ["docx", "pdf"]}
        assert len(calls) == 1

    @pytest.mark.parametrize("side", ["input", "output"])
    def test_strips_blank_lines_and_whitespace(self, side):
        """Both sides should strip blank lines and whitespace identically."""
        from pandoc_cli.commands import info_formats

        flag = f"--list-{side}-formats"
        messy = "\nmarkdown\n  html  \n\nlatex\n\n"

        def fake_run_pandoc(args, *, check=True, capture=True):
            if flag in args:
                return _fake_completed(messy)
            # The other side gets a trivial response so `side='both'` would
            # also work here — but we only invoke the targeted side below.
            return _fake_completed("html\n")

        with patch.object(info_formats, "run_pandoc", side_effect=fake_run_pandoc):
            result = info_formats.run_formats(side=side)

        assert result[side] == ["markdown", "html", "latex"]

    def test_invalid_side_raises_value_error(self):
        from pandoc_cli.commands import info_formats

        with pytest.raises(ValueError):
            info_formats.run_formats(side="bogus")


# ---------------------------------------------------------------------------
# run_engines
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunEngines:
    def test_partitions_engines_into_available_and_missing(self):
        from pandoc_cli.commands import info_engines
        from pandoc_cli import backend

        # Pretend only pdflatex and xelatex exist.
        installed = {"pdflatex", "xelatex"}

        def fake_which(name: str):
            return f"/fake/bin/{name}" if name in installed else None

        with patch.object(info_engines.shutil, "which", side_effect=fake_which):
            result = info_engines.run_engines()

        assert set(result["available"]) == installed
        assert set(result["missing"]) == set(backend.PDF_ENGINES) - installed

    def test_no_engines_installed(self):
        from pandoc_cli.commands import info_engines
        from pandoc_cli import backend

        with patch.object(info_engines.shutil, "which", return_value=None):
            result = info_engines.run_engines()

        assert result["available"] == []
        assert set(result["missing"]) == set(backend.PDF_ENGINES)

    def test_all_engines_installed(self):
        from pandoc_cli.commands import info_engines
        from pandoc_cli import backend

        with patch.object(info_engines.shutil, "which", return_value="/fake/bin/x"):
            result = info_engines.run_engines()

        assert set(result["available"]) == set(backend.PDF_ENGINES)
        assert result["missing"] == []

    def test_total_count_matches_pdf_engines(self):
        from pandoc_cli.commands import info_engines
        from pandoc_cli import backend

        # Sometimes available, sometimes not — the sum must equal len(PDF_ENGINES).
        toggle = iter([True, False] * len(backend.PDF_ENGINES))

        def fake_which(name: str):
            return "/fake/bin/x" if next(toggle) else None

        with patch.object(info_engines.shutil, "which", side_effect=fake_which):
            result = info_engines.run_engines()

        assert len(result["available"]) + len(result["missing"]) == len(backend.PDF_ENGINES)

    def test_concatenation_preserves_pdf_engines_order(self):
        """`run_engines` docstring promises order matches `PDF_ENGINES` within
        each list. The combined `available + missing` sequence (when the two
        partitions are interleaved against the source) must therefore be a
        subsequence-preserving partition of `PDF_ENGINES`. Concretely: filter
        `PDF_ENGINES` by membership in each partition and the result must
        equal that partition exactly."""
        from pandoc_cli.commands import info_engines
        from pandoc_cli import backend

        # Make every other engine available so both partitions are non-empty
        # AND non-trivial (not a contiguous prefix of PDF_ENGINES).
        engines = list(backend.PDF_ENGINES)
        installed = set(engines[::2])  # 0, 2, 4, ...

        def fake_which(name: str):
            return f"/fake/bin/{name}" if name in installed else None

        with patch.object(info_engines.shutil, "which", side_effect=fake_which):
            result = info_engines.run_engines()

        expected_available = [e for e in engines if e in installed]
        expected_missing = [e for e in engines if e not in installed]
        assert result["available"] == expected_available
        assert result["missing"] == expected_missing


# ---------------------------------------------------------------------------
# cmd_formats — Tier 1 CLI dispatch tests
#
# These exercise the Typer command via CliRunner with `run_formats` mocked,
# so subprocess never fires. Verifies dispatch behavior (mutex check, side
# selection, section rendering) that previously only had Tier 2 coverage.
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestCmdFormatsCLI:
    @pytest.fixture
    def runner(self):
        from typer.testing import CliRunner

        return CliRunner()

    @pytest.fixture
    def app(self):
        from pandoc_cli import app as typer_app

        return typer_app

    def test_no_flags_renders_both_sections(self, runner, app):
        from pandoc_cli import info as info_mod

        with patch.object(
            info_mod,
            "run_formats",
            return_value={"input": ["markdown", "html"], "output": ["docx", "pdf"]},
        ) as mock_rf:
            result = runner.invoke(app, ["info", "formats"])

        assert result.exit_code == 0, result.output
        mock_rf.assert_called_once_with(side="both")
        assert "INPUT" in result.stdout
        assert "OUTPUT" in result.stdout
        # Order: INPUT section appears before OUTPUT.
        assert result.stdout.index("INPUT") < result.stdout.index("OUTPUT")

    def test_input_flag_only_renders_input_section(self, runner, app):
        from pandoc_cli import info as info_mod

        with patch.object(
            info_mod,
            "run_formats",
            return_value={"input": ["markdown"], "output": []},
        ) as mock_rf:
            result = runner.invoke(app, ["info", "formats", "--input"])

        assert result.exit_code == 0, result.output
        mock_rf.assert_called_once_with(side="input")
        assert "INPUT" in result.stdout
        assert "OUTPUT" not in result.stdout
        assert "markdown" in result.stdout

    def test_output_flag_only_renders_output_section(self, runner, app):
        from pandoc_cli import info as info_mod

        with patch.object(
            info_mod,
            "run_formats",
            return_value={"input": [], "output": ["docx"]},
        ) as mock_rf:
            result = runner.invoke(app, ["info", "formats", "--output"])

        assert result.exit_code == 0, result.output
        mock_rf.assert_called_once_with(side="output")
        assert "OUTPUT" in result.stdout
        assert "INPUT" not in result.stdout
        assert "docx" in result.stdout

    def test_mutual_exclusion_errors_and_skips_run_formats(self, runner, app):
        """The mutex check must run BEFORE `run_formats` is called — otherwise
        we'd shell out to pandoc twice just to error out."""
        from pandoc_cli import info as info_mod

        with patch.object(info_mod, "run_formats") as mock_rf:
            result = runner.invoke(app, ["info", "formats", "--input", "--output"])

        assert result.exit_code == 1
        assert "mutually exclusive" in result.output.lower()
        mock_rf.assert_not_called()
