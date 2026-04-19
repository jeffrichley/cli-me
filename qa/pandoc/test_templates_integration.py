"""Tier 2: templates command integration tests against the real pandoc binary.

These exercise the full Typer CLI via :class:`typer.testing.CliRunner` and
require a working ``pandoc`` install (the ``pandoc_path`` fixture from
``conftest.py`` skips if missing). Tests that need a LaTeX engine use the
``latex_engine`` fixture (also from ``conftest.py``) which skips cleanly
when no engine is on PATH.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from _pandoc_helpers import assert_file_nonempty, assert_pdf_magic


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
# templates print
# ---------------------------------------------------------------------------


class TestTemplatesPrint:
    def test_latex_template_starts_with_documentclass(self, app, runner):
        result = runner.invoke(app, ["templates", "print", "latex"])
        assert result.exit_code == 0, result.stdout
        assert "\\documentclass" in result.stdout
        # R4 nice-to-fix: every pandoc default template embeds the body via
        # the ``$body$`` interpolation marker. Asserts that pandoc actually
        # emitted a *template* (not, e.g., a help message).
        assert "$body$" in result.stdout

    def test_html5_template_contains_html_marker(self, app, runner):
        result = runner.invoke(app, ["templates", "print", "html5"])
        assert result.exit_code == 0, result.stdout
        # html5 default template starts with <!DOCTYPE html> in older pandoc;
        # newer pandoc emits <!doctype html>. Either way, an <html opener
        # appears later. Test all three to stay version-agnostic.
        lower = result.stdout.lower()
        assert "<!doctype html>" in lower or "<html" in lower, (
            f"No HTML marker in template output (head={result.stdout[:200]!r})"
        )

    def test_unknown_format_exits_non_zero(self, app, runner):
        result = runner.invoke(app, ["templates", "print", "notarealformat"])
        # Pandoc exits non-zero (typically 43) when the writer is unknown.
        # We only care that the wrapper surfaces the failure.
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# templates apply
# ---------------------------------------------------------------------------


class TestTemplatesApply:
    def test_apply_minimal_latex_template_renders_title(
        self, app, runner, md_with_frontmatter: Path, minimal_latex_template: Path, tmp_path: Path
    ):
        out = tmp_path / "out.tex"
        result = runner.invoke(
            app,
            [
                "templates",
                "apply",
                str(md_with_frontmatter),
                str(out),
                "--template",
                str(minimal_latex_template),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert_file_nonempty(out)

        text = out.read_text(encoding="utf-8")
        # The minimal template uses $title$, which the YAML frontmatter sets
        # to "Sample Document" — this proves the template was applied AND
        # variables flowed from frontmatter into the template.
        assert "Sample Document" in text, (
            f"Expected frontmatter title in output; got head={text[:200]!r}"
        )
        # Sanity: the body content also made it through.
        assert "Body" in text or "body" in text.lower()

    def test_apply_with_variable_overrides(
        self, app, runner, md_with_frontmatter: Path, minimal_latex_template: Path, tmp_path: Path
    ):
        out = tmp_path / "out.tex"
        result = runner.invoke(
            app,
            [
                "templates",
                "apply",
                str(md_with_frontmatter),
                str(out),
                "--template",
                str(minimal_latex_template),
                "--variable",
                "title=Overridden Title",
            ],
        )
        assert result.exit_code == 0, result.stdout
        text = out.read_text(encoding="utf-8")
        # -V wins over frontmatter for the template-only namespace.
        assert "Overridden Title" in text

    def test_apply_missing_template_exits_non_zero(
        self, app, runner, simple_md: Path, tmp_path: Path
    ):
        out = tmp_path / "out.tex"
        result = runner.invoke(
            app,
            [
                "templates",
                "apply",
                str(simple_md),
                str(out),
                "--template",
                str(tmp_path / "no-such-template.tex"),
            ],
        )
        assert result.exit_code != 0

    def test_apply_docx_output_emits_silently_ignored_warning(
        self,
        app,
        runner,
        simple_md: Path,
        minimal_latex_template: Path,
        tmp_path: Path,
    ):
        """End-to-end check that the DOCX warning fires against real pandoc.

        Pandoc happily writes a .docx file when given a LaTeX --template
        (silently ignoring the template); our wrapper must still emit the
        guidance pointing the user at --reference-doc.
        """
        out = tmp_path / "out.docx"
        try:
            local_runner = CliRunner(mix_stderr=False)
        except TypeError:
            local_runner = CliRunner()

        result = local_runner.invoke(
            app,
            [
                "templates",
                "apply",
                str(simple_md),
                str(out),
                "--template",
                str(minimal_latex_template),
            ],
        )
        parts = [result.stdout or ""]
        try:
            parts.append(result.stderr or "")
        except ValueError:
            pass
        if result.exception is not None:
            parts.append(str(result.exception))
        combined = "\n".join(parts).lower()

        # Wrapper-level warning is the contract; pandoc's own success/failure
        # is incidental here.
        assert "warning" in combined and "--template" in combined and ".docx" in combined, (
            f"Expected --template ignored warning for .docx output; got:\n{combined}"
        )


# ---------------------------------------------------------------------------
# templates eisvogel — needs a real LaTeX engine
# ---------------------------------------------------------------------------


def _looks_like_environmental_latex_failure(exc: BaseException | None, captured: str) -> str | None:
    """Return a skip reason when a Tier 2 LaTeX failure is environmental.

    Eisvogel needs a working LaTeX engine *plus* a handful of LaTeX packages
    (footnotebackref, mdframed, etc.). On machines where the engine binary is
    on PATH (so the ``latex_engine`` fixture doesn't skip) but MiKTeX/TeX Live
    can't satisfy those packages or the engine fails for unrelated reasons
    (broken MiKTeX install dirs, sandboxed package install blocked, ...), the
    test should skip cleanly rather than red-fail.

    Returns a human-readable reason string when a skip is warranted; ``None``
    otherwise (caller should hard-fail).
    """
    blob = (captured or "")
    if exc is not None:
        # CliRunner stashes the underlying CalledProcessError on result.exception
        for attr in ("stdout", "stderr", "output"):
            extra = getattr(exc, attr, None)
            if isinstance(extra, (bytes, str)):
                blob += "\n" + (extra.decode("utf-8", "replace") if isinstance(extra, bytes) else extra)
        blob += "\n" + str(exc)
    lower = blob.lower()
    # Targeted markers only — the previous catchall "did not succeed" was
    # broad enough to mask wrapper bugs (almost any LaTeX failure surfaces
    # that phrase). R4 fix: keep these tightly scoped to known environmental
    # failure modes, and force unrelated failures to red-fail loudly.
    markers = (
        "footnotebackref.sty",      # Eisvogel-required package missing
        "mdframed",                 # ditto
        "miktex cannot retrieve",   # broken MiKTeX install dir
        "package install",          # sandboxed install blocked
    )
    for m in markers:
        if m in lower:
            return f"Skipping: environmental LaTeX issue (matched {m!r}); not a wrapper bug."
    return None


class TestTemplatesEisvogel:
    def test_eisvogel_produces_pdf(
        self,
        app,
        runner,
        md_with_frontmatter: Path,
        latex_engine: str,  # noqa: ARG002 — skip-gate fixture
        tmp_path: Path,
    ):
        """Tier 2 happy path + Eisvogel-specific marker assertion.

        R4 fix: the original test only asserted the file was a valid PDF,
        which would pass even if a mutation stripped ``--template`` from the
        wrapper (pandoc's default LaTeX template still produces a valid PDF).

        Marker chosen: PDF byte size. The bundled Eisvogel template is a
        ~31KB LaTeX preamble that loads ``mdframed``, ``footnotebackref``,
        custom title-page geometry, etc. The resulting PDF for our small
        fixture is reliably > 50KB; pandoc's default LaTeX template emits a
        far smaller PDF (~30KB or less) for the same input. We pick 50_000
        as a conservative threshold that catches the "ignored template"
        mutation while leaving plenty of headroom for upstream Eisvogel
        revisions.
        """
        out = tmp_path / "out.pdf"
        result = runner.invoke(
            app,
            ["templates", "eisvogel", str(md_with_frontmatter), str(out)],
        )
        if result.exit_code != 0:
            reason = _looks_like_environmental_latex_failure(result.exception, result.stdout or "")
            if reason:
                pytest.skip(reason)
            pytest.fail(
                f"Eisvogel run failed unexpectedly:\nstdout={result.stdout}\n"
                f"exception={result.exception!r}"
            )
        assert_pdf_magic(out)
        # Eisvogel-specific marker: PDF size > 50KB (default pandoc LaTeX
        # output for the same fixture is ~10-30KB; Eisvogel adds the
        # title-page + tcolorbox + mdframed preamble pushing it well over).
        size = out.stat().st_size
        assert size > 50_000, (
            f"PDF only {size} bytes — too small to have used Eisvogel "
            f"preamble (default pandoc LaTeX is ~10-30KB; Eisvogel ~80KB+). "
            f"Possible regression: --template was ignored."
        )

    def test_eisvogel_warns_when_output_not_pdf(
        self,
        app,
        runner,
        md_with_frontmatter: Path,
        latex_engine: str,  # noqa: ARG002 — skip-gate fixture
        tmp_path: Path,
    ):
        # Pandoc inspects the -o extension. With an Eisvogel LaTeX template
        # but a non-PDF output, pandoc may either fail (LaTeX writer can't
        # produce HTML) or succeed and write LaTeX-ish content. Either way
        # we expect our stderr warning to appear in the captured output.
        # We use a fresh CliRunner with mix_stderr=False so we can read
        # stderr separately even when the underlying command exits non-zero.
        out = tmp_path / "out.html"
        try:
            local_runner = CliRunner(mix_stderr=False)
        except TypeError:
            # Newer click no longer accepts mix_stderr; fall back to default.
            local_runner = CliRunner()

        result = local_runner.invoke(
            app,
            ["templates", "eisvogel", str(md_with_frontmatter), str(out)],
        )
        # Combine every available stream — different click/typer versions
        # surface stderr through different attributes.
        parts = [result.stdout or ""]
        try:
            parts.append(result.stderr or "")
        except ValueError:
            # stderr not separately captured — already in stdout.
            pass
        if result.exception is not None:
            parts.append(str(result.exception))
        combined = "\n".join(parts)

        # Our wrapper must emit a warning that mentions PDF / the output ext.
        assert "warning" in combined.lower() and "pdf" in combined.lower(), (
            f"Expected non-PDF warning mentioning 'pdf'; got:\n{combined}"
        )
        # Documented behavior: pandoc may either succeed (writes LaTeX-ish
        # text into the .html path because --template forces the LaTeX
        # writer pipeline) or fail with an engine error. We do NOT assert
        # the exit code here — the warning is the contract.
