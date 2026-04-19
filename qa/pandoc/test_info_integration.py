"""Tier 2: info command integration tests against the real pandoc binary.

These exercise the full Typer CLI via ``CliRunner`` and require a working
``pandoc`` install (the ``pandoc_path`` fixture from ``conftest.py`` skips if
missing).
"""

from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(scope="module")
def app(pandoc_path: str):  # noqa: ARG001 — fixture forces a skip if pandoc missing
    """Import the Typer app once pandoc is known to exist."""
    from pandoc_cli import app as typer_app

    return typer_app


# ---------------------------------------------------------------------------
# info version
# ---------------------------------------------------------------------------


class TestInfoVersion:
    def test_exits_zero(self, app, runner):
        result = runner.invoke(app, ["info", "version"])
        assert result.exit_code == 0, result.stdout

    def test_stdout_matches_version_pattern(self, app, runner):
        result = runner.invoke(app, ["info", "version"])
        assert re.match(r"^\d+\.\d+(\.\d+)*$", result.stdout.strip()), (
            f"Unexpected version stdout: {result.stdout!r}"
        )

    def test_matches_session_pandoc_version(self, app, runner, pandoc_version):
        result = runner.invoke(app, ["info", "version"])
        assert result.stdout.strip() == pandoc_version


# ---------------------------------------------------------------------------
# info formats
# ---------------------------------------------------------------------------


class TestInfoFormats:
    def test_no_flags_shows_both_sections(self, app, runner):
        result = runner.invoke(app, ["info", "formats"])
        assert result.exit_code == 0, result.stdout
        assert "INPUT" in result.stdout
        assert "OUTPUT" in result.stdout

    def test_no_flags_meets_minimum_counts(self, app, runner):
        """Per playbook: input ≥ 50, output ≥ 70 on pandoc 3.9.0.2."""
        result = runner.invoke(app, ["info", "formats"])
        assert result.exit_code == 0

        lines = result.stdout.splitlines()
        # The CLI prints "INPUT", then indented format lines, then a blank,
        # then "OUTPUT", then indented format lines.
        input_idx = lines.index("INPUT")
        output_idx = lines.index("OUTPUT")

        input_formats = [
            ln.strip() for ln in lines[input_idx + 1 : output_idx] if ln.strip()
        ]
        output_formats = [ln.strip() for ln in lines[output_idx + 1 :] if ln.strip()]

        assert len(input_formats) >= 50, (
            f"Expected ≥ 50 input formats, got {len(input_formats)}"
        )
        assert len(output_formats) >= 70, (
            f"Expected ≥ 70 output formats, got {len(output_formats)}"
        )

    def test_no_flags_contains_known_formats(self, app, runner):
        """Partition stdout into INPUT/OUTPUT sections and verify each known
        format appears under the correct section. Catches an input/output swap
        in `cmd_formats` rendering — substring-only checks would miss that.
        """
        result = runner.invoke(app, ["info", "formats"])
        assert result.exit_code == 0, result.stdout

        lines = result.stdout.splitlines()
        input_idx = lines.index("INPUT")
        output_idx = lines.index("OUTPUT")

        input_formats = {
            ln.strip() for ln in lines[input_idx + 1 : output_idx] if ln.strip()
        }
        output_formats = {
            ln.strip() for ln in lines[output_idx + 1 :] if ln.strip()
        }

        # markdown is an input format (and also an output format, but the
        # important assertion is it appears in the INPUT section).
        assert "markdown" in input_formats, (
            f"Expected 'markdown' under INPUT, got input={sorted(input_formats)[:10]}..."
        )
        # docx, latex, html appear in both — assert per-section presence.
        assert "html" in input_formats
        assert "html" in output_formats
        assert "latex" in input_formats
        assert "latex" in output_formats
        assert "docx" in input_formats
        assert "docx" in output_formats

    def test_input_only_omits_output_section(self, app, runner):
        result = runner.invoke(app, ["info", "formats", "--input"])
        assert result.exit_code == 0, result.stdout
        assert "INPUT" in result.stdout
        assert "OUTPUT" not in result.stdout

    def test_output_only_omits_input_section(self, app, runner):
        result = runner.invoke(app, ["info", "formats", "--output"])
        assert result.exit_code == 0, result.stdout
        assert "OUTPUT" in result.stdout
        assert "INPUT" not in result.stdout

    def test_mutual_exclusion(self, app, runner):
        result = runner.invoke(app, ["info", "formats", "--input", "--output"])
        assert result.exit_code == 1
        # CliRunner with mix_stderr=True (the default) merges stderr into
        # result.output. Asserting on .output works whether or not click
        # exposes a separate stderr stream.
        assert "mutually exclusive" in result.output.lower()


# ---------------------------------------------------------------------------
# info engines
# ---------------------------------------------------------------------------


class TestInfoEngines:
    def test_exits_zero(self, app, runner):
        result = runner.invoke(app, ["info", "engines"])
        assert result.exit_code == 0, result.stdout

    def test_has_both_section_headers(self, app, runner):
        result = runner.invoke(app, ["info", "engines"])
        assert "Available" in result.stdout
        assert "Not installed" in result.stdout

    def test_total_engines_listed_matches_pdf_engines(self, app, runner):
        from pandoc_cli import backend

        result = runner.invoke(app, ["info", "engines"])
        # Each engine appears exactly once, either as a bare name (available)
        # or with "(not installed)" suffix (missing). We look for substring
        # presence (engines like "lualatex" wouldn't collide with anything).
        for engine in backend.PDF_ENGINES:
            assert engine in result.stdout, f"Engine {engine} missing from output"

        # Count engines listed under Not installed via the suffix marker.
        missing_count = result.stdout.count("(not installed)")
        # Count engines listed under Available — header line + bare-name lines
        # before the blank line preceding 'Not installed'.
        lines = result.stdout.splitlines()
        avail_idx = lines.index("Available")
        # Find first blank line AFTER Available header, indicating end of the section.
        end_avail = avail_idx + 1
        while end_avail < len(lines) and lines[end_avail].strip() != "":
            end_avail += 1
        available_count = end_avail - (avail_idx + 1)

        assert available_count + missing_count == len(backend.PDF_ENGINES), (
            f"Available={available_count} + Missing={missing_count} != "
            f"len(PDF_ENGINES)={len(backend.PDF_ENGINES)}"
        )

        # Disjointness — no engine should appear in BOTH sections. If
        # `cmd_engines` ever stops partitioning (e.g. listing all engines under
        # both Available and Not installed), the count above could still pass
        # by coincidence. Compare by exact set membership.
        available_engines = {
            ln.strip() for ln in lines[avail_idx + 1 : end_avail] if ln.strip()
        }
        missing_idx = lines.index("Not installed")
        missing_engines = {
            ln.replace("(not installed)", "").strip()
            for ln in lines[missing_idx + 1 :]
            if ln.strip()
        }
        overlap = available_engines & missing_engines
        assert not overlap, f"Engines appearing in BOTH sections: {overlap}"
