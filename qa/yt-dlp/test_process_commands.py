"""Tier 1 command-graph tests for process commands."""

import sys
from pathlib import Path

import pytest

# Add scripts dir so we can import the logic layer directly.
_scripts = str(Path(__file__).resolve().parents[2] / "skill-repo" / "yt-dlp" / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from yt_dlp_cli.commands import process_sponsorblock, process_chapters, process_remux, process_embed

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


# ---------------------------------------------------------------------------
# SponsorBlock
# ---------------------------------------------------------------------------

class TestSponsorBlock:
    @pytest.mark.command_graph
    def test_defaults(self):
        args = process_sponsorblock.build_args(URL)
        assert args[-1] == URL
        assert "--force-overwrites" in args

    @pytest.mark.command_graph
    def test_remove(self):
        args = process_sponsorblock.build_args(URL, remove="sponsor,selfpromo")
        assert "--sponsorblock-remove" in args
        idx = args.index("--sponsorblock-remove")
        assert args[idx + 1] == "sponsor,selfpromo"
        assert args[-1] == URL

    @pytest.mark.command_graph
    def test_mark(self):
        args = process_sponsorblock.build_args(URL, mark="intro,outro")
        assert "--sponsorblock-mark" in args
        idx = args.index("--sponsorblock-mark")
        assert args[idx + 1] == "intro,outro"

    @pytest.mark.command_graph
    def test_force_keyframes(self):
        args = process_sponsorblock.build_args(URL, force_keyframes=True)
        assert "--force-keyframes-at-cuts" in args

    @pytest.mark.command_graph
    def test_format(self):
        args = process_sponsorblock.build_args(URL, format="22")
        assert "-f" in args
        idx = args.index("-f")
        assert args[idx + 1] == "22"

    @pytest.mark.command_graph
    def test_output(self):
        args = process_sponsorblock.build_args(URL, output="%(title)s.%(ext)s")
        assert "-o" in args
        idx = args.index("-o")
        assert args[idx + 1] == "%(title)s.%(ext)s"

    @pytest.mark.command_graph
    def test_output_dir(self):
        args = process_sponsorblock.build_args(URL, output_dir="/tmp/out")
        assert "-P" in args
        idx = args.index("-P")
        assert args[idx + 1] == "/tmp/out"

    @pytest.mark.command_graph
    def test_cookies(self):
        args = process_sponsorblock.build_args(URL, cookies="cookies.txt")
        assert "--cookies" in args
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    @pytest.mark.command_graph
    def test_no_overwrites(self):
        args = process_sponsorblock.build_args(URL, no_overwrites=True)
        assert "--no-overwrites" in args
        assert "--force-overwrites" not in args

    @pytest.mark.command_graph
    def test_defaults_no_sponsorblock_flags(self):
        args = process_sponsorblock.build_args(URL)
        assert "--sponsorblock-remove" not in args
        assert "--sponsorblock-mark" not in args
        assert "--force-keyframes-at-cuts" not in args


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------

class TestChapters:
    @pytest.mark.command_graph
    def test_defaults(self):
        args = process_chapters.build_args(URL)
        assert args[-1] == URL
        assert "--force-overwrites" in args
        assert "--split-chapters" not in args

    @pytest.mark.command_graph
    def test_split(self):
        args = process_chapters.build_args(URL, split=True)
        assert "--split-chapters" in args
        assert args[-1] == URL

    @pytest.mark.command_graph
    def test_remove(self):
        args = process_chapters.build_args(URL, remove="^Intro$")
        assert "--remove-chapters" in args
        idx = args.index("--remove-chapters")
        assert args[idx + 1] == "^Intro$"

    @pytest.mark.command_graph
    def test_format(self):
        args = process_chapters.build_args(URL, format="bv*+ba/b")
        assert "-f" in args
        idx = args.index("-f")
        assert args[idx + 1] == "bv*+ba/b"

    @pytest.mark.command_graph
    def test_output(self):
        args = process_chapters.build_args(URL, output="%(title)s.%(ext)s")
        idx = args.index("-o")
        assert args[idx + 1] == "%(title)s.%(ext)s"

    @pytest.mark.command_graph
    def test_output_dir(self):
        args = process_chapters.build_args(URL, output_dir="/tmp/out")
        idx = args.index("-P")
        assert args[idx + 1] == "/tmp/out"

    @pytest.mark.command_graph
    def test_cookies(self):
        args = process_chapters.build_args(URL, cookies="cookies.txt")
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    @pytest.mark.command_graph
    def test_no_overwrites(self):
        args = process_chapters.build_args(URL, no_overwrites=True)
        assert "--no-overwrites" in args
        assert "--force-overwrites" not in args

    @pytest.mark.command_graph
    def test_force_keyframes(self):
        args = process_chapters.build_args(URL, force_keyframes=True)
        assert "--force-keyframes-at-cuts" in args


# ---------------------------------------------------------------------------
# Remux
# ---------------------------------------------------------------------------

class TestRemux:
    @pytest.mark.command_graph
    def test_defaults(self):
        args = process_remux.build_args(URL)
        assert args[-1] == URL
        assert "--force-overwrites" in args
        assert "--remux-video" in args
        idx = args.index("--remux-video")
        assert args[idx + 1] == "mp4"

    @pytest.mark.command_graph
    def test_custom_container(self):
        args = process_remux.build_args(URL, container="mkv")
        idx = args.index("--remux-video")
        assert args[idx + 1] == "mkv"

    @pytest.mark.command_graph
    def test_output(self):
        args = process_remux.build_args(URL, output="%(title)s.%(ext)s")
        assert "-o" in args
        idx = args.index("-o")
        assert args[idx + 1] == "%(title)s.%(ext)s"

    @pytest.mark.command_graph
    def test_output_dir(self):
        args = process_remux.build_args(URL, output_dir="/tmp/out")
        assert "-P" in args
        idx = args.index("-P")
        assert args[idx + 1] == "/tmp/out"

    @pytest.mark.command_graph
    def test_cookies(self):
        args = process_remux.build_args(URL, cookies="cookies.txt")
        assert "--cookies" in args
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    @pytest.mark.command_graph
    def test_no_overwrites(self):
        args = process_remux.build_args(URL, no_overwrites=True)
        assert "--no-overwrites" in args
        assert "--force-overwrites" not in args

    @pytest.mark.command_graph
    def test_format(self):
        args = process_remux.build_args(URL, format="bv*+ba/b")
        idx = args.index("-f")
        assert args[idx + 1] == "bv*+ba/b"


# ---------------------------------------------------------------------------
# Embed
# ---------------------------------------------------------------------------

class TestEmbed:
    @pytest.mark.command_graph
    def test_defaults(self):
        args = process_embed.build_args(URL)
        assert args[-1] == URL
        assert "--force-overwrites" in args
        # No embed flags by default
        assert "--embed-subs" not in args
        assert "--embed-thumbnail" not in args
        assert "--embed-metadata" not in args
        assert "--embed-chapters" not in args
        assert "--embed-info-json" not in args

    @pytest.mark.command_graph
    def test_subs(self):
        args = process_embed.build_args(URL, subs=True)
        assert "--embed-subs" in args

    @pytest.mark.command_graph
    def test_thumbnail(self):
        args = process_embed.build_args(URL, thumbnail=True)
        assert "--embed-thumbnail" in args

    @pytest.mark.command_graph
    def test_metadata(self):
        args = process_embed.build_args(URL, metadata=True)
        assert "--embed-metadata" in args

    @pytest.mark.command_graph
    def test_chapters(self):
        args = process_embed.build_args(URL, chapters=True)
        assert "--embed-chapters" in args

    @pytest.mark.command_graph
    def test_info_json(self):
        args = process_embed.build_args(URL, info_json=True)
        assert "--embed-info-json" in args

    @pytest.mark.command_graph
    def test_sub_langs(self):
        args = process_embed.build_args(URL, sub_langs="en,es")
        assert "--sub-langs" in args
        idx = args.index("--sub-langs")
        assert args[idx + 1] == "en,es"

    @pytest.mark.command_graph
    def test_format(self):
        args = process_embed.build_args(URL, format="22")
        assert "-f" in args
        idx = args.index("-f")
        assert args[idx + 1] == "22"

    @pytest.mark.command_graph
    def test_output(self):
        args = process_embed.build_args(URL, output="%(title)s.%(ext)s")
        idx = args.index("-o")
        assert args[idx + 1] == "%(title)s.%(ext)s"

    @pytest.mark.command_graph
    def test_output_dir(self):
        args = process_embed.build_args(URL, output_dir="/tmp/out")
        idx = args.index("-P")
        assert args[idx + 1] == "/tmp/out"

    @pytest.mark.command_graph
    def test_cookies(self):
        args = process_embed.build_args(URL, cookies="cookies.txt")
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    @pytest.mark.command_graph
    def test_no_overwrites(self):
        args = process_embed.build_args(URL, no_overwrites=True)
        assert "--no-overwrites" in args
        assert "--force-overwrites" not in args

    @pytest.mark.command_graph
    def test_subs_also_writes_subs(self):
        args = process_embed.build_args(URL, subs=True)
        assert "--write-subs" in args
        assert "--embed-subs" in args

    @pytest.mark.command_graph
    def test_subs_only_no_other_embeds(self):
        args = process_embed.build_args(URL, subs=True)
        assert "--embed-subs" in args
        assert "--embed-thumbnail" not in args
        assert "--embed-metadata" not in args
        assert "--embed-chapters" not in args
        assert "--embed-info-json" not in args

    @pytest.mark.command_graph
    def test_thumbnail_only_no_other_embeds(self):
        args = process_embed.build_args(URL, thumbnail=True)
        assert "--embed-thumbnail" in args
        assert "--embed-subs" not in args
        assert "--embed-metadata" not in args
        assert "--embed-chapters" not in args
        assert "--embed-info-json" not in args

    @pytest.mark.command_graph
    def test_metadata_only_no_other_embeds(self):
        args = process_embed.build_args(URL, metadata=True)
        assert "--embed-metadata" in args
        assert "--embed-subs" not in args
        assert "--embed-thumbnail" not in args
        assert "--embed-chapters" not in args
        assert "--embed-info-json" not in args

    @pytest.mark.command_graph
    def test_all_embeds(self):
        """All embed flags together."""
        args = process_embed.build_args(
            URL,
            subs=True,
            thumbnail=True,
            metadata=True,
            chapters=True,
            info_json=True,
        )
        assert "--embed-subs" in args
        assert "--embed-thumbnail" in args
        assert "--embed-metadata" in args
        assert "--embed-chapters" in args
        assert "--embed-info-json" in args
        assert args[-1] == URL
