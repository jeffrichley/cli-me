"""Tier 1: Command-graph tests for the download command group.

These tests verify that the logic layer builds the correct yt-dlp argument lists.
No binary needed — pure unit tests.
"""

import sys
import pytest

# Add the scripts directory to the path so we can import the commands module
sys.path.insert(
    0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "skill-repo" / "yt-dlp" / "scripts")
)

from yt_dlp_cli.commands import download_video, download_audio, download_playlist, download_channel


# ─── download_video ──────────────────────────────────────────────────────────

@pytest.mark.command_graph
class TestDownloadVideo:
    URL = "https://www.youtube.com/watch?v=TEST123"

    def test_default_args(self):
        args = download_video.build_args(self.URL)
        assert "-f" in args
        assert "bv*+ba/b" in args
        assert "--force-overwrites" in args
        assert args[-1] == self.URL

    def test_format_selection(self):
        args = download_video.build_args(self.URL, format="22")
        idx = args.index("-f")
        assert args[idx + 1] == "22"

    def test_max_height(self):
        args = download_video.build_args(self.URL, max_height=720)
        assert "-S" in args
        idx = args.index("-S")
        assert args[idx + 1] == "res:720"

    def test_format_takes_precedence_over_max_height(self):
        args = download_video.build_args(self.URL, format="22", max_height=720)
        idx = args.index("-f")
        assert args[idx + 1] == "22"
        assert "-S" not in args

    def test_output_template(self):
        args = download_video.build_args(self.URL, output="%(title)s.%(ext)s")
        assert "-o" in args
        idx = args.index("-o")
        assert args[idx + 1] == "%(title)s.%(ext)s"

    def test_output_directory(self):
        args = download_video.build_args(self.URL, output_dir="/tmp/downloads")
        assert "-P" in args
        idx = args.index("-P")
        assert args[idx + 1] == "/tmp/downloads"

    def test_no_overwrites(self):
        args = download_video.build_args(self.URL, no_overwrites=True)
        assert "--no-overwrites" in args
        assert "--force-overwrites" not in args

    def test_cookies(self):
        args = download_video.build_args(self.URL, cookies="cookies.txt")
        assert "--cookies" in args
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    def test_embed_all(self):
        args = download_video.build_args(
            self.URL,
            embed_metadata=True,
            embed_subs=True,
            embed_thumbnail=True,
            embed_chapters=True,
        )
        assert "--embed-metadata" in args
        assert "--embed-subs" in args
        assert "--embed-thumbnail" in args
        assert "--embed-chapters" in args

    def test_sponsorblock(self):
        args = download_video.build_args(self.URL, sponsorblock_remove="sponsor,selfpromo")
        assert "--sponsorblock-remove" in args
        idx = args.index("--sponsorblock-remove")
        assert args[idx + 1] == "sponsor,selfpromo"

    def test_performance_flags(self):
        args = download_video.build_args(self.URL, concurrent_fragments=4, rate_limit="50K")
        idx_n = args.index("-N")
        assert args[idx_n + 1] == "4"
        idx_r = args.index("-r")
        assert args[idx_r + 1] == "50K"

    def test_max_filesize(self):
        args = download_video.build_args(self.URL, max_filesize="100M")
        assert "--max-filesize" in args
        idx = args.index("--max-filesize")
        assert args[idx + 1] == "100M"

    def test_extra_args(self):
        args = download_video.build_args(self.URL, extra_args=["--verbose", "--write-info-json"])
        assert "--verbose" in args
        assert "--write-info-json" in args

    def test_defaults_no_embed_flags(self):
        args = download_video.build_args(self.URL)
        assert "--embed-metadata" not in args
        assert "--embed-subs" not in args
        assert "--embed-thumbnail" not in args
        assert "--embed-chapters" not in args
        assert "--sponsorblock-remove" not in args

    def test_url_is_always_last(self):
        args = download_video.build_args(
            self.URL, format="22", output="out.mp4", cookies="c.txt"
        )
        assert args[-1] == self.URL

    def test_concurrent_fragments_zero(self):
        args = download_video.build_args(self.URL, concurrent_fragments=0)
        assert "-N" in args
        idx = args.index("-N")
        assert args[idx + 1] == "0"


# ─── download_audio ──────────────────────────────────────────────────────────

@pytest.mark.command_graph
class TestDownloadAudio:
    URL = "https://www.youtube.com/watch?v=AUDIO123"

    def test_default_args(self):
        args = download_audio.build_args(self.URL)
        assert "-x" in args
        assert "--audio-format" in args
        idx = args.index("--audio-format")
        assert args[idx + 1] == "mp3"
        assert "--audio-quality" in args
        assert "--force-overwrites" in args
        assert args[-1] == self.URL

    def test_format_flac(self):
        args = download_audio.build_args(self.URL, format="flac")
        idx = args.index("--audio-format")
        assert args[idx + 1] == "flac"

    def test_quality_best(self):
        args = download_audio.build_args(self.URL, quality="best")
        idx = args.index("--audio-quality")
        assert args[idx + 1] == "0"

    def test_quality_worst(self):
        args = download_audio.build_args(self.URL, quality="worst")
        idx = args.index("--audio-quality")
        assert args[idx + 1] == "10"

    def test_quality_raw_kbps(self):
        args = download_audio.build_args(self.URL, quality="192")
        idx = args.index("--audio-quality")
        assert args[idx + 1] == "192"

    def test_embed_metadata_and_thumbnail(self):
        args = download_audio.build_args(
            self.URL, embed_metadata=True, embed_thumbnail=True
        )
        assert "--embed-metadata" in args
        assert "--embed-thumbnail" in args

    def test_output_template(self):
        args = download_audio.build_args(self.URL, output="%(title)s.%(ext)s")
        idx = args.index("-o")
        assert args[idx + 1] == "%(title)s.%(ext)s"

    def test_output_directory(self):
        args = download_audio.build_args(self.URL, output_dir="/tmp/audio")
        idx = args.index("-P")
        assert args[idx + 1] == "/tmp/audio"

    def test_no_overwrites(self):
        args = download_audio.build_args(self.URL, no_overwrites=True)
        assert "--no-overwrites" in args
        assert "--force-overwrites" not in args

    def test_rate_limit(self):
        args = download_audio.build_args(self.URL, rate_limit="1M")
        idx = args.index("-r")
        assert args[idx + 1] == "1M"

    def test_cookies(self):
        args = download_audio.build_args(self.URL, cookies="cookies.txt")
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    def test_quality_high(self):
        args = download_audio.build_args(self.URL, quality="high")
        idx = args.index("--audio-quality")
        assert args[idx + 1] == "2"

    def test_quality_low(self):
        args = download_audio.build_args(self.URL, quality="low")
        idx = args.index("--audio-quality")
        assert args[idx + 1] == "8"

    def test_quality_medium_default(self):
        args = download_audio.build_args(self.URL)
        idx = args.index("--audio-quality")
        assert args[idx + 1] == "5"

    def test_url_is_always_last(self):
        args = download_audio.build_args(self.URL, format="opus", quality="best")
        assert args[-1] == self.URL


# ─── download_playlist ───────────────────────────────────────────────────────

@pytest.mark.command_graph
class TestDownloadPlaylist:
    URL = "https://www.youtube.com/playlist?list=PLtest123"

    def test_default_args(self):
        args = download_playlist.build_args(self.URL)
        assert "--yes-playlist" in args
        assert "-f" in args
        assert "-o" in args
        assert "-i" in args  # ignore errors for playlists
        assert "--force-overwrites" in args
        assert args[-1] == self.URL

    def test_default_output_template_contains_playlist(self):
        args = download_playlist.build_args(self.URL)
        idx = args.index("-o")
        assert "playlist_title" in args[idx + 1]
        assert "playlist_index" in args[idx + 1]

    def test_items_selection(self):
        args = download_playlist.build_args(self.URL, items="1:5")
        assert "-I" in args
        idx = args.index("-I")
        assert args[idx + 1] == "1:5"

    def test_archive(self):
        args = download_playlist.build_args(self.URL, archive="archive.txt")
        assert "--download-archive" in args
        idx = args.index("--download-archive")
        assert args[idx + 1] == "archive.txt"

    def test_date_filters(self):
        args = download_playlist.build_args(
            self.URL, date_after="20240101", date_before="20240131"
        )
        idx_after = args.index("--dateafter")
        assert args[idx_after + 1] == "20240101"
        idx_before = args.index("--datebefore")
        assert args[idx_before + 1] == "20240131"

    def test_max_downloads(self):
        args = download_playlist.build_args(self.URL, max_downloads=10)
        assert "--max-downloads" in args
        idx = args.index("--max-downloads")
        assert args[idx + 1] == "10"

    def test_sleep_intervals(self):
        args = download_playlist.build_args(
            self.URL, sleep_interval=2.0, max_sleep_interval=5.0
        )
        idx_sleep = args.index("--sleep-interval")
        assert args[idx_sleep + 1] == "2.0"
        idx_max = args.index("--max-sleep-interval")
        assert args[idx_max + 1] == "5.0"

    def test_cookies(self):
        args = download_playlist.build_args(self.URL, cookies="cookies.txt")
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    def test_no_overwrites(self):
        args = download_playlist.build_args(self.URL, no_overwrites=True)
        assert "--no-overwrites" in args
        assert "--force-overwrites" not in args

    def test_concurrent_fragments(self):
        args = download_playlist.build_args(self.URL, concurrent_fragments=4)
        idx = args.index("-N")
        assert args[idx + 1] == "4"

    def test_rate_limit(self):
        args = download_playlist.build_args(self.URL, rate_limit="1M")
        idx = args.index("-r")
        assert args[idx + 1] == "1M"

    def test_max_downloads_zero(self):
        args = download_playlist.build_args(self.URL, max_downloads=0)
        assert "--max-downloads" in args
        idx = args.index("--max-downloads")
        assert args[idx + 1] == "0"

    def test_url_is_always_last(self):
        args = download_playlist.build_args(self.URL, archive="a.txt", items="1:3")
        assert args[-1] == self.URL


# ─── download_channel ────────────────────────────────────────────────────────

@pytest.mark.command_graph
class TestDownloadChannel:
    URL = "https://www.youtube.com/@TestChannel"

    def test_default_args(self):
        args = download_channel.build_args(self.URL)
        assert "-f" in args
        assert "-o" in args
        assert "-i" in args  # ignore errors for channels
        assert "--force-overwrites" in args
        assert args[-1] == self.URL

    def test_default_output_template_contains_channel(self):
        args = download_channel.build_args(self.URL)
        idx = args.index("-o")
        assert "channel" in args[idx + 1]
        assert "upload_date" in args[idx + 1]

    def test_archive(self):
        args = download_channel.build_args(self.URL, archive="channel_archive.txt")
        idx = args.index("--download-archive")
        assert args[idx + 1] == "channel_archive.txt"

    def test_break_on_existing(self):
        args = download_channel.build_args(self.URL, break_on_existing=True)
        assert "--break-on-existing" in args

    def test_date_range(self):
        args = download_channel.build_args(
            self.URL, date_after="20240101", date_before="20240630"
        )
        idx_after = args.index("--dateafter")
        assert args[idx_after + 1] == "20240101"
        idx_before = args.index("--datebefore")
        assert args[idx_before + 1] == "20240630"

    def test_cookies(self):
        args = download_channel.build_args(self.URL, cookies="cookies.txt")
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    def test_no_overwrites(self):
        args = download_channel.build_args(self.URL, no_overwrites=True)
        assert "--no-overwrites" in args
        assert "--force-overwrites" not in args

    def test_max_downloads(self):
        args = download_channel.build_args(self.URL, max_downloads=10)
        idx = args.index("--max-downloads")
        assert args[idx + 1] == "10"

    def test_concurrent_fragments(self):
        args = download_channel.build_args(self.URL, concurrent_fragments=4)
        idx = args.index("-N")
        assert args[idx + 1] == "4"

    def test_rate_limit(self):
        args = download_channel.build_args(self.URL, rate_limit="1M")
        idx = args.index("-r")
        assert args[idx + 1] == "1M"

    def test_output_template(self):
        args = download_channel.build_args(self.URL, output="custom/%(title)s.%(ext)s")
        idx = args.index("-o")
        assert args[idx + 1] == "custom/%(title)s.%(ext)s"

    def test_output_directory(self):
        args = download_channel.build_args(self.URL, output_dir="/tmp/channel")
        idx = args.index("-P")
        assert args[idx + 1] == "/tmp/channel"

    def test_format(self):
        args = download_channel.build_args(self.URL, format="bv*+ba/b")
        idx = args.index("-f")
        assert args[idx + 1] == "bv*+ba/b"

    def test_sleep_intervals(self):
        args = download_channel.build_args(self.URL, sleep_interval=2.0, max_sleep_interval=5.0)
        idx_s = args.index("--sleep-interval")
        assert args[idx_s + 1] == "2.0"
        idx_m = args.index("--max-sleep-interval")
        assert args[idx_m + 1] == "5.0"

    def test_url_is_always_last(self):
        args = download_channel.build_args(self.URL, archive="a.txt")
        assert args[-1] == self.URL


# ─── format test missing from TestDownloadPlaylist ────────────────────────────

# (added here as a standalone; the class above is complete but was missing this)
def test_download_playlist_format_selection():
    args = download_playlist.build_args(
        "https://www.youtube.com/playlist?list=PLtest123", format="22"
    )
    idx = args.index("-f")
    assert args[idx + 1] == "22"


# ─── Combination tests ────────────────────────────────────────────────────────

def _check_no_duplicate_flags(args: list[str]) -> None:
    """Assert no flag appears more than once in the argument list."""
    flag_counts: dict[str, int] = {}
    for arg in args:
        if arg.startswith("-"):
            flag_counts[arg] = flag_counts.get(arg, 0) + 1
    for flag, count in flag_counts.items():
        assert count == 1, f"Duplicate flag: {flag} appears {count} times"


@pytest.mark.command_graph
class TestDownloadVideoCombination:
    def test_all_params_simultaneously(self):
        """Verify all parameters coexist without collisions."""
        args = download_video.build_args(
            "URL",
            format="22",
            max_height=720,
            output="%(title)s.%(ext)s",
            output_dir="/tmp",
            no_overwrites=True,
            cookies="cookies.txt",
            embed_metadata=True,
            embed_subs=True,
            embed_thumbnail=True,
            embed_chapters=True,
            sponsorblock_remove="sponsor",
            concurrent_fragments=4,
            rate_limit="1M",
            max_filesize="500M",
            extra_args=["--verbose"],
        )
        _check_no_duplicate_flags(args)
        assert args[-1] == "URL"


@pytest.mark.command_graph
class TestDownloadAudioCombination:
    def test_all_params_simultaneously(self):
        """Verify all parameters coexist without collisions."""
        args = download_audio.build_args(
            "URL",
            format="flac",
            quality="best",
            output="%(title)s.%(ext)s",
            output_dir="/tmp",
            cookies="cookies.txt",
            embed_metadata=True,
            embed_thumbnail=True,
            no_overwrites=True,
            rate_limit="1M",
            extra_args=["--verbose"],
        )
        _check_no_duplicate_flags(args)
        assert args[-1] == "URL"


@pytest.mark.command_graph
class TestDownloadPlaylistCombination:
    def test_all_params_simultaneously(self):
        """Verify all parameters coexist without collisions."""
        args = download_playlist.build_args(
            "URL",
            format="22",
            output="%(title)s.%(ext)s",
            output_dir="/tmp",
            items="1:5",
            archive="archive.txt",
            cookies="cookies.txt",
            no_overwrites=True,
            concurrent_fragments=4,
            rate_limit="1M",
            sleep_interval=1.0,
            max_sleep_interval=3.0,
            date_after="20240101",
            date_before="20241231",
            max_downloads=10,
            extra_args=["--verbose"],
        )
        _check_no_duplicate_flags(args)
        assert args[-1] == "URL"


@pytest.mark.command_graph
class TestDownloadChannelCombination:
    def test_all_params_simultaneously(self):
        """Verify all parameters coexist without collisions."""
        args = download_channel.build_args(
            "URL",
            format="22",
            output="%(title)s.%(ext)s",
            output_dir="/tmp",
            archive="archive.txt",
            cookies="cookies.txt",
            no_overwrites=True,
            concurrent_fragments=4,
            rate_limit="1M",
            sleep_interval=1.0,
            max_sleep_interval=3.0,
            date_after="20240101",
            date_before="20241231",
            max_downloads=10,
            break_on_existing=True,
            extra_args=["--verbose"],
        )
        _check_no_duplicate_flags(args)
        assert args[-1] == "URL"
