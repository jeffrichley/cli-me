"""Tests for batch search command arg building."""

from yt_dlp_cli.commands.batch_search import build_args


def test_default_provider_is_youtube():
    args = build_args("test query", max_results=3)
    assert args[-1] == "ytsearch3:test query"


def test_soundcloud_provider():
    args = build_args("test query", max_results=5, provider="soundcloud")
    assert args[-1] == "scsearch5:test query"


def test_invalid_provider_raises():
    import pytest
    with pytest.raises(ValueError, match="Unknown search provider"):
        build_args("test query", provider="fakeprovider")


def test_search_query_is_last_arg():
    args = build_args("test query", format="bestaudio", provider="youtube")
    assert args[-1] == "ytsearch5:test query"
