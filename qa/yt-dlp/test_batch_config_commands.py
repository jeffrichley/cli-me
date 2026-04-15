"""Tier 1: Command-graph tests for the batch and config command groups.

These tests verify that the logic layer builds the correct yt-dlp argument lists.
No binary needed — pure unit tests.
"""

import sys
import pytest

# Add the scripts directory to the path so we can import the commands module
sys.path.insert(
    0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "skill-repo" / "yt-dlp" / "scripts")
)

from yt_dlp_cli.commands import batch_from_file, batch_sync, batch_search
from yt_dlp_cli.commands import config_cookies, config_archive


# ─── batch_from_file ────────────────────────────────────────────────────────

@pytest.mark.command_graph
class TestBatchFromFile:
    FILE = "urls.txt"

    def test_default_args(self):
        args = batch_from_file.build_args(self.FILE)
        assert "--force-overwrites" in args
        assert "-i" in args
        assert "-a" in args
        idx = args.index("-a")
        assert args[idx + 1] == self.FILE

    def test_file_is_last(self):
        args = batch_from_file.build_args(self.FILE, format="22", cookies="c.txt")
        # -a FILE should be the last two elements
        assert args[-2] == "-a"
        assert args[-1] == self.FILE

    def test_format_selection(self):
        args = batch_from_file.build_args(self.FILE, format="bestvideo+bestaudio")
        idx = args.index("-f")
        assert args[idx + 1] == "bestvideo+bestaudio"

    def test_output_template(self):
        args = batch_from_file.build_args(self.FILE, output="%(title)s.%(ext)s")
        idx = args.index("-o")
        assert args[idx + 1] == "%(title)s.%(ext)s"

    def test_output_directory(self):
        args = batch_from_file.build_args(self.FILE, output_dir="/tmp/batch")
        idx = args.index("-P")
        assert args[idx + 1] == "/tmp/batch"

    def test_archive(self):
        args = batch_from_file.build_args(self.FILE, archive="archive.txt")
        assert "--download-archive" in args
        idx = args.index("--download-archive")
        assert args[idx + 1] == "archive.txt"

    def test_cookies(self):
        args = batch_from_file.build_args(self.FILE, cookies="cookies.txt")
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    def test_performance_flags(self):
        args = batch_from_file.build_args(
            self.FILE, concurrent_fragments=4, rate_limit="1M"
        )
        assert "-N" in args
        assert "4" in args
        assert "-r" in args
        assert "1M" in args

    def test_sleep_intervals(self):
        args = batch_from_file.build_args(
            self.FILE, sleep_interval=2.0, max_sleep_interval=5.0
        )
        assert "--sleep-interval" in args
        assert "--max-sleep-interval" in args

    def test_max_downloads(self):
        args = batch_from_file.build_args(self.FILE, max_downloads=10)
        idx = args.index("--max-downloads")
        assert args[idx + 1] == "10"

    def test_extra_args(self):
        args = batch_from_file.build_args(self.FILE, extra_args=["--verbose"])
        assert "--verbose" in args


# ─── batch_sync ─────────────────────────────────────────────────────────────

@pytest.mark.command_graph
class TestBatchSync:
    URL = "https://www.youtube.com/playlist?list=PLtest123"
    ARCHIVE = "sync_archive.txt"

    def test_default_args(self):
        args = batch_sync.build_args(self.URL, archive=self.ARCHIVE)
        assert "--download-archive" in args
        idx = args.index("--download-archive")
        assert args[idx + 1] == self.ARCHIVE
        assert "--force-overwrites" in args
        assert "-i" in args
        assert args[-1] == self.URL

    def test_url_is_last(self):
        args = batch_sync.build_args(
            self.URL, archive=self.ARCHIVE, format="22", cookies="c.txt"
        )
        assert args[-1] == self.URL

    def test_format_selection(self):
        args = batch_sync.build_args(self.URL, archive=self.ARCHIVE, format="best")
        idx = args.index("-f")
        assert args[idx + 1] == "best"

    def test_output_template(self):
        args = batch_sync.build_args(
            self.URL, archive=self.ARCHIVE, output="%(title)s.%(ext)s"
        )
        idx = args.index("-o")
        assert args[idx + 1] == "%(title)s.%(ext)s"

    def test_output_directory(self):
        args = batch_sync.build_args(
            self.URL, archive=self.ARCHIVE, output_dir="/tmp/sync"
        )
        idx = args.index("-P")
        assert args[idx + 1] == "/tmp/sync"

    def test_break_on_existing(self):
        args = batch_sync.build_args(
            self.URL, archive=self.ARCHIVE, break_on_existing=True
        )
        assert "--break-on-existing" in args

    def test_break_on_existing_default_off(self):
        args = batch_sync.build_args(self.URL, archive=self.ARCHIVE)
        assert "--break-on-existing" not in args

    def test_cookies(self):
        args = batch_sync.build_args(
            self.URL, archive=self.ARCHIVE, cookies="cookies.txt"
        )
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    def test_sleep_intervals(self):
        args = batch_sync.build_args(
            self.URL, archive=self.ARCHIVE,
            sleep_interval=1.0, max_sleep_interval=3.0,
        )
        assert "--sleep-interval" in args
        assert "--max-sleep-interval" in args

    def test_max_downloads(self):
        args = batch_sync.build_args(
            self.URL, archive=self.ARCHIVE, max_downloads=5
        )
        idx = args.index("--max-downloads")
        assert args[idx + 1] == "5"

    def test_extra_args(self):
        args = batch_sync.build_args(
            self.URL, archive=self.ARCHIVE, extra_args=["--write-info-json"]
        )
        assert "--write-info-json" in args


# ─── batch_search ───────────────────────────────────────────────────────────

@pytest.mark.command_graph
class TestBatchSearch:
    QUERY = "python tutorial"

    def test_default_args(self):
        args = batch_search.build_args(self.QUERY)
        assert "--force-overwrites" in args
        assert args[-1] == "ytsearch5:python tutorial"

    def test_query_is_last(self):
        args = batch_search.build_args(self.QUERY, format="22", cookies="c.txt")
        assert args[-1].startswith("ytsearch")
        assert self.QUERY in args[-1]

    def test_max_results(self):
        args = batch_search.build_args(self.QUERY, max_results=10)
        assert args[-1] == "ytsearch10:python tutorial"

    def test_format_selection(self):
        args = batch_search.build_args(self.QUERY, format="best")
        idx = args.index("-f")
        assert args[idx + 1] == "best"

    def test_output_template(self):
        args = batch_search.build_args(self.QUERY, output="%(title)s.%(ext)s")
        idx = args.index("-o")
        assert args[idx + 1] == "%(title)s.%(ext)s"

    def test_output_directory(self):
        args = batch_search.build_args(self.QUERY, output_dir="/tmp/search")
        idx = args.index("-P")
        assert args[idx + 1] == "/tmp/search"

    def test_cookies(self):
        args = batch_search.build_args(self.QUERY, cookies="cookies.txt")
        idx = args.index("--cookies")
        assert args[idx + 1] == "cookies.txt"

    def test_extra_args(self):
        args = batch_search.build_args(self.QUERY, extra_args=["--flat-playlist"])
        assert "--flat-playlist" in args


# ─── config_cookies ─────────────────────────────────────────────────────────

@pytest.mark.command_graph
class TestConfigCookies:

    def test_default_args(self):
        args = config_cookies.build_args(browser="chrome")
        assert "--cookies-from-browser" in args
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "chrome"
        assert "--cookies" in args
        cidx = args.index("--cookies")
        assert args[cidx + 1] == "cookies.txt"
        assert "--skip-download" in args
        assert "--force-overwrites" in args
        # Dummy URL must be last
        assert args[-1] == "https://www.youtube.com/"

    def test_custom_output(self):
        args = config_cookies.build_args(browser="firefox", output="my_cookies.txt")
        cidx = args.index("--cookies")
        assert args[cidx + 1] == "my_cookies.txt"

    def test_profile(self):
        args = config_cookies.build_args(browser="chrome", profile="Default")
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "chrome:Default"

    def test_container(self):
        args = config_cookies.build_args(browser="firefox", container="Work")
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "firefox::Work"

    def test_profile_and_container(self):
        args = config_cookies.build_args(
            browser="firefox", profile="default-release", container="Shopping"
        )
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "firefox:default-release::Shopping"

    def test_keyring(self):
        args = config_cookies.build_args(browser="chrome", keyring="gnomekeyring")
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "chrome+gnomekeyring"

    def test_keyring_uses_plus_prefix(self):
        args = config_cookies.build_args(browser="chrome", keyring="gnomekeyring")
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "chrome+gnomekeyring"

    def test_container_uses_double_colon(self):
        args = config_cookies.build_args(browser="firefox", container="Work")
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "firefox::Work"

    def test_profile_and_container_double_colon(self):
        args = config_cookies.build_args(browser="firefox", profile="default", container="Work")
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "firefox:default::Work"

    def test_keyring_plus_profile(self):
        args = config_cookies.build_args(browser="chrome", keyring="gnomekeyring", profile="Default")
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "chrome+gnomekeyring:Default"

    def test_all_fields(self):
        args = config_cookies.build_args(
            browser="firefox", keyring="gnomekeyring", profile="default", container="Work"
        )
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "firefox+gnomekeyring:default::Work"

    def test_dummy_url_is_last(self):
        args = config_cookies.build_args(
            browser="edge", profile="Profile 1", output="edge_cookies.txt"
        )
        assert args[-1] == "https://www.youtube.com/"


# ─── config_archive ─────────────────────────────────────────────────────────

@pytest.mark.command_graph
class TestConfigArchiveCheck:
    ARCHIVE = "archive.txt"
    URL = "https://www.youtube.com/watch?v=TEST123"

    def test_check_args(self):
        args = config_archive.build_check_args(self.ARCHIVE, self.URL)
        assert "--download-archive" in args
        idx = args.index("--download-archive")
        assert args[idx + 1] == self.ARCHIVE
        assert "--simulate" in args
        assert args[-1] == self.URL

    def test_check_no_force_write(self):
        args = config_archive.build_check_args(self.ARCHIVE, self.URL)
        assert "--force-write-archive" not in args

    def test_check_url_is_last(self):
        args = config_archive.build_check_args(self.ARCHIVE, self.URL)
        assert args[-1] == self.URL


@pytest.mark.command_graph
class TestConfigArchiveAdd:
    ARCHIVE = "archive.txt"
    URL = "https://www.youtube.com/watch?v=ADD456"

    def test_add_args(self):
        args = config_archive.build_add_args(self.ARCHIVE, self.URL)
        assert "--download-archive" in args
        idx = args.index("--download-archive")
        assert args[idx + 1] == self.ARCHIVE
        assert "--simulate" in args
        assert "--force-write-archive" in args
        assert args[-1] == self.URL

    def test_add_url_is_last(self):
        args = config_archive.build_add_args(self.ARCHIVE, self.URL)
        assert args[-1] == self.URL
