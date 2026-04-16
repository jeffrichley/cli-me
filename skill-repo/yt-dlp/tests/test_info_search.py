"""Tests for info search command arg building."""

import json
from yt_dlp_cli.commands.info_search import build_args, format_pretty


def test_default_args_include_no_download():
    args = build_args("test query")
    assert "--dump-json" in args
    assert "--no-download" in args


def test_default_provider_is_youtube():
    args = build_args("test query", max_results=3)
    assert "ytsearch3:test query" in args


def test_soundcloud_provider():
    args = build_args("test query", provider="soundcloud", max_results=2)
    assert "scsearch2:test query" in args


def test_does_not_include_force_overwrites():
    args = build_args("test query")
    assert "--force-overwrites" not in args


def test_cookies_passed_through():
    args = build_args("test query", cookies="/tmp/cookies.txt")
    assert "--cookies" in args
    assert "/tmp/cookies.txt" in args


def test_search_query_is_last():
    args = build_args("test query", cookies="/tmp/c.txt")
    assert args[-1] == "ytsearch5:test query"


def test_format_pretty_single_result():
    result = {
        "title": "My Video",
        "webpage_url": "https://example.com/watch?v=abc",
        "duration_string": "3:45",
        "uploader": "SomeChannel",
    }
    output = format_pretty(result)
    assert "My Video" in output
    assert "https://example.com/watch?v=abc" in output
    assert "3:45" in output
    assert "SomeChannel" in output


def test_format_pretty_missing_fields():
    result = {"title": "Minimal"}
    output = format_pretty(result)
    assert "Minimal" in output
