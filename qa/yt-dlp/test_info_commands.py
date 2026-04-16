"""Tier 1 command-graph tests for info commands.

These tests verify that build_args() produces the correct yt-dlp argument
lists without invoking the real executable.
"""

import sys
from pathlib import Path

import pytest

# Add scripts dir to path so we can import the logic layer directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skill-repo" / "yt-dlp" / "scripts"))

from yt_dlp_cli.commands import info_formats, info_metadata, info_subtitles, info_thumbnails

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


# ── info_formats ────────────────────────────────────────────────────


@pytest.mark.command_graph
class TestInfoFormats:
    def test_default_lists_formats(self):
        args = info_formats.build_args(URL)
        assert args == ["-F", URL]

    def test_url_is_last(self):
        args = info_formats.build_args(URL)
        assert args[-1] == URL

    def test_json_output(self):
        args = info_formats.build_json_args(URL)
        assert args == ["-j", URL]

    def test_json_url_is_last(self):
        args = info_formats.build_json_args(URL)
        assert args[-1] == URL

    def test_cookies(self):
        args = info_formats.build_args(URL, cookies="cookies.txt")
        assert "--cookies" in args
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    def test_json_cookies(self):
        args = info_formats.build_json_args(URL, cookies="cookies.txt")
        assert "--cookies" in args
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"


# ── info_metadata ───────────────────────────────────────────────────


@pytest.mark.command_graph
class TestInfoMetadata:
    def test_default_dumps_json(self):
        args = info_metadata.build_args(URL)
        assert "--dump-json" in args
        assert "--skip-download" in args
        assert args[-1] == URL

    def test_default_does_not_write_file(self):
        args = info_metadata.build_args(URL)
        assert "--write-info-json" not in args
        assert "--no-download" not in args

    def test_write_json_mode(self):
        args = info_metadata.build_args(URL, write_json=True)
        assert "--write-info-json" in args
        assert "--skip-download" in args
        assert "--dump-json" not in args
        assert args[-1] == URL

    def test_output_dir(self):
        args = info_metadata.build_args(URL, output_dir="/tmp/out")
        assert "-P" in args
        assert args[args.index("-P") + 1] == "/tmp/out"
        assert args[-1] == URL

    def test_cookies(self):
        args = info_metadata.build_args(URL, cookies="cookies.txt")
        assert "--cookies" in args
        assert args[args.index("--cookies") + 1] == "cookies.txt"
        assert args[-1] == URL

    def test_all_options(self):
        args = info_metadata.build_args(
            URL, write_json=True, output_dir="/tmp", cookies="c.txt"
        )
        assert "--write-info-json" in args
        assert "--skip-download" in args
        assert "-P" in args
        assert "--cookies" in args
        assert args[-1] == URL


# ── info_subtitles ──────────────────────────────────────────────────


@pytest.mark.command_graph
class TestInfoSubtitles:
    def test_default_lists_subs(self):
        args = info_subtitles.build_args(URL)
        assert args == ["--list-subs", URL]

    def test_url_is_last(self):
        args = info_subtitles.build_args(URL)
        assert args[-1] == URL

    def test_download_mode(self):
        args = info_subtitles.build_args(URL, download=True)
        assert "--write-subs" in args
        assert "--skip-download" in args
        assert "--list-subs" not in args
        assert args[-1] == URL

    def test_langs_filter(self):
        args = info_subtitles.build_args(URL, langs="en,es")
        assert "--sub-langs" in args
        assert args[args.index("--sub-langs") + 1] == "en,es"
        assert args[-1] == URL

    def test_format_option(self):
        args = info_subtitles.build_args(URL, format="srt")
        assert "--sub-format" in args
        assert args[args.index("--sub-format") + 1] == "srt"
        assert args[-1] == URL

    def test_cookies(self):
        args = info_subtitles.build_args(URL, cookies="cookies.txt")
        assert "--cookies" in args
        assert args[args.index("--cookies") + 1] == "cookies.txt"
        assert args[-1] == URL

    def test_download_with_langs_and_format(self):
        args = info_subtitles.build_args(
            URL, download=True, langs="en", format="vtt"
        )
        assert "--write-subs" in args
        assert "--skip-download" in args
        assert "--sub-langs" in args
        assert "--sub-format" in args
        assert args[-1] == URL

    def test_auto_subs(self):
        args = info_subtitles.build_args(URL, download=True, auto_subs=True)
        assert "--write-auto-subs" in args
        assert "--write-subs" in args

    def test_auto_subs_ignored_without_download(self):
        args = info_subtitles.build_args(URL, auto_subs=True)
        assert "--write-auto-subs" not in args


# ── info_thumbnails ─────────────────────────────────────────────────


@pytest.mark.command_graph
class TestInfoThumbnails:
    def test_default_lists_thumbnails(self):
        args = info_thumbnails.build_args(URL)
        assert args == ["--list-thumbnails", URL]

    def test_url_is_last(self):
        args = info_thumbnails.build_args(URL)
        assert args[-1] == URL

    def test_download_mode(self):
        args = info_thumbnails.build_args(URL, download=True)
        assert "--write-thumbnail" in args
        assert "--skip-download" in args
        assert "--list-thumbnails" not in args
        assert args[-1] == URL

    def test_cookies(self):
        args = info_thumbnails.build_args(URL, cookies="cookies.txt")
        assert "--cookies" in args
        assert args[args.index("--cookies") + 1] == "cookies.txt"
        assert args[-1] == URL

    def test_convert_option(self):
        args = info_thumbnails.build_args(URL, download=True, convert="jpg")
        assert "--convert-thumbnails" in args
        assert args[args.index("--convert-thumbnails") + 1] == "jpg"
        assert args[-1] == URL

    def test_convert_without_download(self):
        args = info_thumbnails.build_args(URL, convert="jpg")
        # In list mode, convert is still emitted (yt-dlp ignores it)
        assert "--list-thumbnails" in args

    def test_all_options(self):
        args = info_thumbnails.build_args(
            URL, download=True, cookies="c.txt", convert="png"
        )
        assert "--write-thumbnail" in args
        assert "--skip-download" in args
        assert "--cookies" in args
        assert "--convert-thumbnails" in args
        assert args[-1] == URL
