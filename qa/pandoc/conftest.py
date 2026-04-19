"""Shared fixtures for pandoc QA tests.

These fixtures are consumed by both Tier 1 (mocked) and Tier 2 (real-binary)
tests across all 5 command groups (info, convert, citations, templates,
filters). New shared fixtures should land here; group-specific setup belongs
in the per-group test files.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Make the skill's scripts/ directory importable so `from pandoc_cli...`
# resolves in tests.
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "skill-repo"
    / "pandoc"
    / "scripts"
)
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Also add qa/pandoc/ so test files can `from _pandoc_helpers import ...`
# (pytest's importlib mode does NOT auto-add the test dir to sys.path.
# Name is _pandoc_helpers (not _helpers) to avoid collision with the
# top-level qa/_helpers.py used by the ffmpeg suite.)
_QA_PANDOC_DIR = Path(__file__).resolve().parent
if str(_QA_PANDOC_DIR) not in sys.path:
    sys.path.insert(0, str(_QA_PANDOC_DIR))


# ---------------------------------------------------------------------------
# Engine-availability fixtures — skip integration tests cleanly when the
# wrapped tool or a dependent engine isn't installed on this machine.
# ---------------------------------------------------------------------------


def _which(name: str) -> str | None:
    path = shutil.which(name)
    if path is not None:
        return path
    # Windows winget install path for pandoc when not on PATH for fresh shells
    if sys.platform == "win32" and name == "pandoc":
        for candidate in (
            r"C:\Program Files\Pandoc\pandoc.exe",
            r"C:\Program Files (x86)\Pandoc\pandoc.exe",
        ):
            if Path(candidate).exists():
                return candidate
    return None


@pytest.fixture(scope="session")
def pandoc_path() -> str:
    """Path to the installed pandoc binary, or skip if missing."""
    path = _which("pandoc")
    if path is None:
        pytest.skip("pandoc not installed")
    return path


@pytest.fixture(scope="session")
def pandoc_version(pandoc_path: str) -> str:
    """Installed pandoc version string (e.g. '3.9.0.2')."""
    result = subprocess.run(
        [pandoc_path, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    first_line = result.stdout.split("\n", 1)[0]
    parts = first_line.split()
    return parts[1] if len(parts) >= 2 else "unknown"


@pytest.fixture(scope="session")
def latex_engine() -> str:
    """A LaTeX-class PDF engine (pdflatex / xelatex / lualatex / tectonic) or skip."""
    for engine in ("pdflatex", "xelatex", "lualatex", "tectonic"):
        path = _which(engine)
        if path is not None:
            return engine
    pytest.skip("No LaTeX PDF engine found (need pdflatex / xelatex / lualatex / tectonic)")


@pytest.fixture(scope="session")
def html_pdf_engine() -> str:
    """An HTML-based PDF engine (weasyprint / wkhtmltopdf / prince) or skip."""
    for engine in ("weasyprint", "wkhtmltopdf", "prince", "pagedjs-cli"):
        path = _which(engine)
        if path is not None:
            return engine
    pytest.skip("No HTML-based PDF engine found (need weasyprint / wkhtmltopdf / prince / pagedjs-cli)")


@pytest.fixture(scope="session")
def has_pandoc_crossref() -> bool:
    """True if pandoc-crossref is on PATH; integration tests for the filter
    sub-command should skip when False."""
    return _which("pandoc-crossref") is not None


# ---------------------------------------------------------------------------
# Source content fixtures — small but realistic markdown / bib / template
# files written into tmp_path on demand.
# ---------------------------------------------------------------------------


_SIMPLE_MD = """\
# Heading One

This is the first paragraph with **bold** and *italic* text.

## Heading Two

A second-level section.

- Item one
- Item two
- Item three
"""


@pytest.fixture
def simple_md(tmp_path: Path) -> Path:
    """A small markdown file: 1 H1, 1 H2, 1 paragraph, 1 bullet list."""
    p = tmp_path / "simple.md"
    p.write_text(_SIMPLE_MD, encoding="utf-8")
    return p


_MD_WITH_FRONTMATTER = """\
---
title: Sample Document
author: Jeff Richley
date: 2026-04-19
abstract: A short abstract for the test fixture.
keywords: [test, fixture, pandoc]
---

# Body

The frontmatter above sets `title`, `author`, `date`, `abstract`, and
`keywords`. Pandoc reads them into the `Meta` map.
"""


@pytest.fixture
def md_with_frontmatter(tmp_path: Path) -> Path:
    """A markdown file with a YAML metadata block."""
    p = tmp_path / "frontmatter.md"
    p.write_text(_MD_WITH_FRONTMATTER, encoding="utf-8")
    return p


_MD_WITH_CITATIONS = """\
---
bibliography: refs.bib
---

# Cited Paper

According to @smith2020, the result is significant. Earlier work
[@jones2019, p. 33] established the baseline. See also [@brown2021;
@smith2020].

# References
"""


@pytest.fixture
def md_with_citations(tmp_path: Path) -> Path:
    """A markdown file with three citation references and a Reference heading."""
    p = tmp_path / "cited.md"
    p.write_text(_MD_WITH_CITATIONS, encoding="utf-8")
    return p


_SIMPLE_BIB = """\
@article{smith2020,
  author = {Smith, Jane},
  title = {A Foundational Result},
  journal = {Journal of Examples},
  year = {2020},
  volume = {12},
  number = {3},
  pages = {45--67},
}

@book{jones2019,
  author = {Jones, Robert},
  title = {Introduction to Test Fixtures},
  publisher = {Sample Press},
  year = {2019},
  address = {New York},
}

@inproceedings{brown2021,
  author = {Brown, Alice and Davis, Carlos},
  title = {Subsequent Work},
  booktitle = {Proceedings of the Test Conference},
  year = {2021},
  pages = {1--10},
}
"""


@pytest.fixture
def simple_bib(tmp_path: Path) -> Path:
    """A small BibTeX file with three entries: smith2020, jones2019, brown2021."""
    p = tmp_path / "refs.bib"
    p.write_text(_SIMPLE_BIB, encoding="utf-8")
    return p


# A working Lua filter — verified against pandoc 3.9.0.2 in Phase 1d. Header
# is a Block, so walk_block is the correct walker.
_LUA_UPPERCASE_HEADINGS = """\
function Header(el)
  return pandoc.walk_block(el, {
    Str = function(s) return pandoc.Str(string.upper(s.text)) end
  })
end
"""


@pytest.fixture
def lua_uppercase_filter(tmp_path: Path) -> Path:
    """A Lua filter that uppercases every word in every Header. Verified working."""
    p = tmp_path / "uppercase.lua"
    p.write_text(_LUA_UPPERCASE_HEADINGS, encoding="utf-8")
    return p


# A minimal LaTeX template that uses just $title$ and $body$ — enough to
# verify --template plumbing without depending on pandoc's full default.
_MINIMAL_LATEX_TEMPLATE = r"""\documentclass{article}
\usepackage{geometry}
\title{$title$}
\begin{document}
\maketitle
$body$
\end{document}
"""


@pytest.fixture
def minimal_latex_template(tmp_path: Path) -> Path:
    """A minimal LaTeX template using $title$ and $body$."""
    p = tmp_path / "minimal.tex"
    p.write_text(_MINIMAL_LATEX_TEMPLATE, encoding="utf-8")
    return p


# Output-verification helpers moved to qa/pandoc/_pandoc_helpers.py.
# (Conftest is auto-loaded by pytest, not meant to be imported by name.)
# Tests use: from _pandoc_helpers import assert_pdf_magic, assert_docx_magic, ...
