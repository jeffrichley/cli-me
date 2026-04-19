"""Output-format verification helpers for pandoc QA integration tests.

Importable as ``from _helpers import assert_pdf_magic, ...``. These live in
their own module (not in conftest.py) because conftest is meant to be
auto-loaded by pytest, not imported by name — `from conftest import ...`
is unreliable under ``--import-mode=importlib`` (the cli-me default).
"""

from __future__ import annotations

from pathlib import Path


def assert_file_nonempty(path: Path) -> None:
    """Assert a file exists and is not empty."""
    assert path.exists(), f"Output does not exist: {path}"
    assert path.stat().st_size > 0, f"Output is empty: {path}"


def assert_pdf_magic(path: Path) -> None:
    """Assert a file starts with the PDF magic bytes (%PDF-)."""
    assert_file_nonempty(path)
    with open(path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-", f"Not a PDF: header was {header!r}"


def assert_docx_magic(path: Path) -> None:
    """Assert a file starts with the ZIP magic bytes (DOCX is a zip)."""
    assert_file_nonempty(path)
    with open(path, "rb") as f:
        header = f.read(2)
    assert header == b"PK", f"Not a DOCX (zip): header was {header!r}"


def assert_html_doctype(path: Path) -> None:
    """Assert a file starts with `<!DOCTYPE html>` (case-insensitive)."""
    assert_file_nonempty(path)
    head = path.read_text(encoding="utf-8")[:200].lower()
    assert "<!doctype html>" in head, f"Not standalone HTML: {head[:60]!r}"


def assert_epub_magic(path: Path) -> None:
    """Assert a file is an EPUB (zip starting with PK + 'mimetype' early)."""
    assert_file_nonempty(path)
    with open(path, "rb") as f:
        data = f.read(64)
    assert data[:2] == b"PK", f"Not an EPUB (zip): header was {data[:2]!r}"
    assert b"mimetype" in data, "EPUB should have 'mimetype' near the start"
