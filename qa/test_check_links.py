"""Tests for the markdown link/orphan checker."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_links import find_md_files, extract_relative_links, check_links, check_orphans


class TestExtractRelativeLinks:
    def test_standard_link(self):
        links = extract_relative_links("[Foo](bar.md)")
        assert links == [("bar.md", None)]

    def test_link_with_anchor(self):
        links = extract_relative_links("[Foo](bar.md#section)")
        assert links == [("bar.md", "section")]

    def test_ignores_http_urls(self):
        links = extract_relative_links("[Foo](https://example.com)")
        assert links == []

    def test_ignores_absolute_paths(self):
        links = extract_relative_links("[Foo](/absolute/path.md)")
        assert links == []

    def test_multiple_links(self):
        text = "[A](a.md) some text [B](sub/b.md)"
        links = extract_relative_links(text)
        assert ("a.md", None) in links
        assert ("sub/b.md", None) in links

    def test_parent_directory_link(self):
        links = extract_relative_links("[Up](../other.md)")
        assert links == [("../other.md", None)]


class TestCheckLinks:
    def test_valid_link(self, tmp_path):
        index = tmp_path / "index.md"
        target = tmp_path / "page.md"
        index.write_text("[Page](page.md)")
        target.write_text("# Page")
        broken = check_links(tmp_path)
        assert broken == []

    def test_broken_link(self, tmp_path):
        index = tmp_path / "index.md"
        index.write_text("[Missing](missing.md)")
        broken = check_links(tmp_path)
        assert len(broken) == 1
        assert broken[0]["target"] == "missing.md"
        assert "index.md" in broken[0]["source"]

    def test_subdirectory_link(self, tmp_path):
        index = tmp_path / "index.md"
        sub = tmp_path / "sub"
        sub.mkdir()
        target = sub / "page.md"
        index.write_text("[Sub](sub/page.md)")
        target.write_text("# Sub page")
        broken = check_links(tmp_path)
        assert broken == []

    def test_broken_subdirectory_link(self, tmp_path):
        index = tmp_path / "index.md"
        index.write_text("[Sub](sub/missing.md)")
        broken = check_links(tmp_path)
        assert len(broken) == 1


class TestCheckOrphans:
    def test_no_orphans(self, tmp_path):
        index = tmp_path / "index.md"
        page = tmp_path / "page.md"
        index.write_text("[Page](page.md)")
        page.write_text("# Page")
        orphans = check_orphans(tmp_path)
        assert orphans == []

    def test_finds_orphan(self, tmp_path):
        index = tmp_path / "index.md"
        page = tmp_path / "page.md"
        orphan = tmp_path / "forgotten.md"
        index.write_text("[Page](page.md)")
        page.write_text("# Page")
        orphan.write_text("# I am lost")
        orphans = check_orphans(tmp_path)
        assert len(orphans) == 1
        assert "forgotten.md" in orphans[0]

    def test_excludes_skill_md(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        index = tmp_path / "index.md"
        skill.write_text("# Skill")
        index.write_text("nothing links here but index is a root")
        orphans = check_orphans(tmp_path)
        assert not any("SKILL.md" in o for o in orphans)

    def test_mutually_linked_files(self, tmp_path):
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        a.write_text("[B](b.md)")
        b.write_text("[A](a.md)")
        orphans = check_orphans(tmp_path)
        assert orphans == []
