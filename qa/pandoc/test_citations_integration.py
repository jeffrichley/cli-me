"""Tier 2: citations render — real pandoc binary, real bibliography.

Drives `pandoc-cli citations render` end-to-end via Typer's CliRunner and
asserts on the produced files (HTML/DOCX magic, rendered citation text,
References section). Skipped cleanly when pandoc isn't installed.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pandoc_cli import app

from _pandoc_helpers import (
    assert_docx_magic,
    assert_file_nonempty,
    assert_html_doctype,
    assert_pdf_magic,
)


def _docx_text(path: Path) -> str:
    """Return the plain-text content of a DOCX's word/document.xml.

    DOCX is a zip; word/document.xml holds the body OOXML. Strip XML tags
    so callers can grep for rendered citation strings without worrying
    about the surrounding markup.
    """
    with zipfile.ZipFile(path) as zf:
        with zf.open("word/document.xml") as f:
            xml = f.read().decode("utf-8", errors="replace")
    # Strip tags: leaves visible text (good enough for substring assertions).
    return re.sub(r"<[^>]+>", " ", xml)


def _pdf_text(path: Path) -> str | None:
    """Return PDF text via pdftotext or pypdf, or None if neither available.

    Returns None when no extraction tool is available so the caller can
    pytest.skip with a clear reason instead of silently passing.
    """
    if shutil.which("pdftotext") is not None:
        result = subprocess.run(
            ["pdftotext", str(path), "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout
    try:
        import pypdf  # type: ignore[import-not-found]
    except ImportError:
        return None
    reader = pypdf.PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


pytestmark = pytest.mark.integration


@pytest.fixture
def runner() -> CliRunner:
    # mix_stderr=False so we can assert on stderr separately for warning checks.
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Happy-path: HTML and DOCX rendered with a real bibliography
# ---------------------------------------------------------------------------


def test_render_to_html_contains_smith_and_references(
    runner: CliRunner,
    tmp_path: Path,
    md_with_citations: Path,
    simple_bib: Path,
    pandoc_path: str,
) -> None:
    out = tmp_path / "cited.html"

    # md_with_citations declares `bibliography: refs.bib` in frontmatter; the
    # CLI overrides it with --bibliography pointing to the real fixture path.
    result = runner.invoke(
        app,
        [
            "citations", "render",
            str(md_with_citations),
            str(out),
            "--bibliography", str(simple_bib),
            "--standalone",
        ],
    )

    assert result.exit_code == 0, f"stderr: {result.stderr}"
    assert_html_doctype(out)

    text = out.read_text(encoding="utf-8")
    # smith2020 → "Smith" must be rendered into the HTML body.
    assert "Smith" in text, "Expected rendered author 'Smith' in HTML output"
    # The fixture cites brown2021 (multi-author: Brown and Davis). At least
    # the first author must appear in the in-text citation; both must
    # appear in the bibliography. Author-date styles render only the lead
    # author in-text, so assert "Brown" appears anywhere and "Davis"
    # appears in the bibliography section.
    assert "Brown" in text, "Expected multi-author 'Brown' in HTML output"
    assert "Davis" in text, (
        "Expected co-author 'Davis' in HTML output (bibliography entry)"
    )
    # The fixture uses [@jones2019, p. 33] — the page locator must render.
    # chicago-author-date renders this as something like "(Jones 2019, 33)".
    # Allow either "p. 33" or just "33" near "Jones" to survive style swaps.
    assert "33" in text, "Expected page locator '33' to render in HTML"

    # Pandoc's default chicago-author-date emits a section heading or div for
    # the reference list. Accept either the heading we wrote (`# References`)
    # being preserved or pandoc's auto-generated id="refs" div.
    has_refs_marker = (
        re.search(r"(?i)references|bibliography|works cited", text) is not None
        or 'id="refs"' in text
    )
    assert has_refs_marker, "Expected a References / Bibliography marker in HTML"


def test_render_to_docx_writes_valid_docx(
    runner: CliRunner,
    tmp_path: Path,
    md_with_citations: Path,
    simple_bib: Path,
    pandoc_path: str,
) -> None:
    out = tmp_path / "cited.docx"

    result = runner.invoke(
        app,
        [
            "citations", "render",
            str(md_with_citations),
            str(out),
            "--bibliography", str(simple_bib),
        ],
    )

    assert result.exit_code == 0, f"stderr: {result.stderr}"
    assert_docx_magic(out)
    # Extract word/document.xml and assert the rendered citation actually
    # made it into the body. Without this, a regression that produced
    # raw `[@smith2020]` (e.g. from a --biblatex swap) would still pass
    # the magic-bytes check.
    text = _docx_text(out)
    assert "Smith" in text, (
        f"Expected rendered author 'Smith' in DOCX body; got: {text[:300]!r}"
    )


# ---------------------------------------------------------------------------
# Pandoc-side warnings: unknown citation key
# ---------------------------------------------------------------------------


def test_render_unknown_citation_key_warns_but_succeeds(
    runner: CliRunner,
    tmp_path: Path,
    simple_bib: Path,
    pandoc_path: str,
) -> None:
    bad_md = tmp_path / "bad.md"
    bad_md.write_text(
        "# Doc\n\nThis cites [@nonexistent_key_999].\n\n# References\n",
        encoding="utf-8",
    )
    out = tmp_path / "bad.html"

    result = runner.invoke(
        app,
        [
            "citations", "render",
            str(bad_md),
            str(out),
            "--bibliography", str(simple_bib),
            "--standalone",
        ],
    )

    # Per playbook: pandoc emits a warning but exits 0 on missing citation key.
    assert result.exit_code == 0, f"stderr: {result.stderr}"
    assert_html_doctype(out)
    # Pandoc's exact wording: "[WARNING] Citeproc: citation nonexistent_key_999 not found"
    assert "not found" in result.stderr.lower(), (
        f"Expected 'not found' warning in stderr; got: {result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Wrapper-side validation: missing inputs
# ---------------------------------------------------------------------------


def test_render_missing_bibliography_file_exits_one(
    runner: CliRunner,
    tmp_path: Path,
    md_with_citations: Path,
    pandoc_path: str,
) -> None:
    out = tmp_path / "out.html"
    missing_bib = tmp_path / "does_not_exist.bib"

    result = runner.invoke(
        app,
        [
            "citations", "render",
            str(md_with_citations),
            str(out),
            "--bibliography", str(missing_bib),
        ],
    )

    assert result.exit_code == 1
    assert "bibliography" in result.stderr.lower()
    assert not out.exists(), "Output should not be created when bib is missing"


def test_render_missing_input_file_exits_one(
    runner: CliRunner,
    tmp_path: Path,
    simple_bib: Path,
    pandoc_path: str,
) -> None:
    out = tmp_path / "out.html"
    missing_in = tmp_path / "does_not_exist.md"

    result = runner.invoke(
        app,
        [
            "citations", "render",
            str(missing_in),
            str(out),
            "--bibliography", str(simple_bib),
        ],
    )

    assert result.exit_code == 1
    assert "input" in result.stderr.lower()
    assert not out.exists(), "Output should not be created when input is missing"


# ---------------------------------------------------------------------------
# PDF render — only when a LaTeX engine is installed
# ---------------------------------------------------------------------------


def test_render_to_pdf_when_latex_available(
    runner: CliRunner,
    tmp_path: Path,
    md_with_citations: Path,
    simple_bib: Path,
    pandoc_path: str,
    latex_engine: str,
) -> None:
    out = tmp_path / "cited.pdf"

    result = runner.invoke(
        app,
        [
            "citations", "render",
            str(md_with_citations),
            str(out),
            "--bibliography", str(simple_bib),
            "--standalone",
        ],
    )

    assert result.exit_code == 0, f"stderr: {result.stderr}"
    assert_pdf_magic(out)
    assert_file_nonempty(out)

    # Try to extract the PDF text and confirm the citation rendered. If
    # neither pdftotext nor pypdf is available, skip with a clear reason
    # rather than silently leaving the gap.
    text = _pdf_text(out)
    if text is None:
        pytest.skip(
            "PDF text extraction tool not available (need pdftotext or "
            "pypdf); this test only verified %PDF- magic"
        )
    assert "Smith" in text, (
        f"Expected rendered author 'Smith' in PDF text; got: {text[:300]!r}"
    )


# ---------------------------------------------------------------------------
# --csl flag end-to-end: explicit CSL files from disk
# ---------------------------------------------------------------------------


# A minimal but valid CSL 1.0 stylesheet. Renders citations as "(AUTHOR YEAR)"
# and a one-line bibliography entry. Enough to verify --csl plumbing
# end-to-end without depending on Zotero's hosted style library.
_MINIMAL_CSL = """\
<?xml version="1.0" encoding="utf-8"?>
<style xmlns="http://purl.org/net/xbiblio/csl" version="1.0" class="in-text">
  <info>
    <title>Minimal Test Style</title>
    <id>http://example.com/styles/minimal-test</id>
    <updated>2026-04-18T00:00:00+00:00</updated>
  </info>
  <citation>
    <layout prefix="(" suffix=")" delimiter="; ">
      <names variable="author">
        <name form="short"/>
      </names>
      <text macro="year-block" prefix=" "/>
    </layout>
  </citation>
  <bibliography>
    <layout>
      <names variable="author">
        <name and="text" delimiter-precedes-last="never"/>
      </names>
      <text macro="year-block" prefix=" (" suffix=")"/>
      <text variable="title" prefix=". "/>
      <text value="."/>
    </layout>
  </bibliography>
  <macro name="year-block">
    <date variable="issued">
      <date-part name="year"/>
    </date>
  </macro>
</style>
"""


def test_render_with_explicit_csl_renders_citation(
    runner: CliRunner,
    tmp_path: Path,
    md_with_citations: Path,
    simple_bib: Path,
    pandoc_path: str,
) -> None:
    """An explicit --csl file changes the rendered citation format."""
    csl = tmp_path / "minimal.csl"
    csl.write_text(_MINIMAL_CSL, encoding="utf-8")
    out = tmp_path / "cited.html"

    result = runner.invoke(
        app,
        [
            "citations", "render",
            str(md_with_citations),
            str(out),
            "--bibliography", str(simple_bib),
            "--csl", str(csl),
            "--standalone",
        ],
    )

    assert result.exit_code == 0, f"stderr: {result.stderr}"
    assert_html_doctype(out)
    body = out.read_text(encoding="utf-8")
    # Author surname must still render through the custom CSL.
    assert "Smith" in body, "Expected 'Smith' rendered through custom CSL"


def test_render_with_pandoc_default_csl(
    runner: CliRunner,
    tmp_path: Path,
    md_with_citations: Path,
    simple_bib: Path,
    pandoc_path: str,
) -> None:
    """Pandoc ships a default.csl data file; passing it via --csl works."""
    # Pull the bundled default.csl out of pandoc's data files so we don't
    # depend on hosted style URLs.
    default_csl = subprocess.run(
        [pandoc_path, "--print-default-data-file=default.csl"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    csl = tmp_path / "default.csl"
    csl.write_text(default_csl, encoding="utf-8")
    out = tmp_path / "cited.html"

    result = runner.invoke(
        app,
        [
            "citations", "render",
            str(md_with_citations),
            str(out),
            "--bibliography", str(simple_bib),
            "--csl", str(csl),
            "--standalone",
        ],
    )

    assert result.exit_code == 0, f"stderr: {result.stderr}"
    body = out.read_text(encoding="utf-8")
    assert "Smith" in body, "Expected 'Smith' rendered through default CSL"


def test_render_with_missing_csl_exits_one_before_pandoc(
    runner: CliRunner,
    tmp_path: Path,
    md_with_citations: Path,
    simple_bib: Path,
    pandoc_path: str,
) -> None:
    """R3 fix: missing --csl path exits 1 with our clean message,
    not pandoc's 6-line Haskell `withBinaryFile` traceback."""
    out = tmp_path / "out.html"
    missing_csl = tmp_path / "does_not_exist.csl"

    result = runner.invoke(
        app,
        [
            "citations", "render",
            str(md_with_citations),
            str(out),
            "--bibliography", str(simple_bib),
            "--csl", str(missing_csl),
        ],
    )

    assert result.exit_code == 1
    assert "csl" in result.stderr.lower()
    assert "not found" in result.stderr.lower()
    # Critically: the Haskell traceback marker must NOT appear — our
    # pre-flight should have caught this before pandoc was invoked.
    assert "withBinaryFile" not in result.stderr
    assert not out.exists(), "Output should not be created when CSL is missing"
