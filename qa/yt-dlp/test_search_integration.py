"""Tier 2: Integration tests for search commands against real yt-dlp.

These tests perform real searches and verify output structure.
Skips if yt-dlp is not installed.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Add the scripts directory to the path
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "skill-repo" / "yt-dlp" / "scripts")
)

from yt_dlp_cli.commands import info_search, batch_search
from yt_dlp_cli.commands.search_providers import PROVIDERS


@pytest.mark.integration
class TestInfoSearchIntegration:
    """Integration tests for info search (search-only, no download)."""

    def test_youtube_search_returns_json(self, ytdlp_path):
        """Search YouTube and verify JSON output structure."""
        args = info_search.build_args("test", max_results=2)
        result = subprocess.run(
            [ytdlp_path] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"yt-dlp failed: {result.stderr}"

        # Parse the output — should be one JSON object per line
        results = info_search.parse_results(result.stdout)
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"

        # Each result must have core fields
        for r in results:
            assert "id" in r, "Result missing 'id' field"
            assert "title" in r, "Result missing 'title' field"
            assert "webpage_url" in r, "Result missing 'webpage_url' field"
            assert r["webpage_url"].startswith("https://"), f"Bad URL: {r['webpage_url']}"

    def test_youtube_search_single_result(self, ytdlp_path):
        """Search with max_results=1 returns exactly 1 result."""
        args = info_search.build_args("python tutorial", max_results=1)
        result = subprocess.run(
            [ytdlp_path] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"yt-dlp failed: {result.stderr}"
        results = info_search.parse_results(result.stdout)
        assert len(results) == 1

    def test_soundcloud_search(self, ytdlp_path):
        """Search SoundCloud and verify extractor is correct."""
        args = info_search.build_args("test", max_results=1, provider="soundcloud")
        result = subprocess.run(
            [ytdlp_path] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"yt-dlp failed: {result.stderr}"

        results = info_search.parse_results(result.stdout)
        assert len(results) == 1
        assert results[0].get("extractor_key", "").lower() == "soundcloud", \
            f"Expected soundcloud extractor, got {results[0].get('extractor_key')}"

    def test_pretty_format_output(self, ytdlp_path):
        """Verify format_output produces valid pretty output from real data."""
        args = info_search.build_args("test", max_results=1)
        result = subprocess.run(
            [ytdlp_path] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0

        results = info_search.parse_results(result.stdout)
        pretty = info_search.format_output(results, pretty=True)
        assert "[1]" in pretty
        assert results[0]["title"] in pretty

    def test_json_format_output(self, ytdlp_path):
        """Verify format_output produces valid JSON from real data."""
        args = info_search.build_args("test", max_results=1)
        result = subprocess.run(
            [ytdlp_path] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0

        results = info_search.parse_results(result.stdout)
        json_output = info_search.format_output(results, pretty=False)
        parsed = json.loads(json_output)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert "title" in parsed[0]

    def test_invalid_provider_raises_before_subprocess(self):
        """Invalid provider raises ValueError without calling yt-dlp."""
        with pytest.raises(ValueError, match="Unknown search provider"):
            info_search.build_args("test", provider="nonexistent")

    def test_no_files_downloaded(self, ytdlp_path, tmp_path):
        """Search must not download any files."""
        args = info_search.build_args("test", max_results=1)
        subprocess.run(
            [ytdlp_path] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(tmp_path),
        )
        # tmp_path should be empty — no files downloaded
        files = list(tmp_path.iterdir())
        assert len(files) == 0, f"Search downloaded files: {files}"


@pytest.mark.integration
class TestBatchSearchIntegration:
    """Integration tests for batch search arg building with real providers."""

    def test_all_providers_produce_valid_prefix(self):
        """Every registered provider produces a valid yt-dlp search prefix."""
        for name, prefix in PROVIDERS.items():
            args = batch_search.build_args("test", max_results=1, provider=name)
            last = args[-1]
            assert last.startswith(prefix), \
                f"Provider '{name}' produced last arg '{last}', expected prefix '{prefix}'"
            assert ":test" in last, f"Query not in last arg: {last}"
