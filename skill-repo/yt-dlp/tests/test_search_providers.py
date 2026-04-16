"""Tests for the search providers module."""

from yt_dlp_cli.commands.search_providers import (
    PROVIDERS,
    get_search_prefix,
    provider_names,
)
import pytest


def test_providers_map_has_youtube():
    assert "youtube" in PROVIDERS
    assert PROVIDERS["youtube"] == "ytsearch"


def test_providers_map_has_soundcloud():
    assert "soundcloud" in PROVIDERS
    assert PROVIDERS["soundcloud"] == "scsearch"


def test_providers_map_has_youtube_music():
    assert "youtube-music" in PROVIDERS
    assert PROVIDERS["youtube-music"] == "ytmsearch"


def test_get_search_prefix_valid():
    assert get_search_prefix("youtube") == "ytsearch"
    assert get_search_prefix("soundcloud") == "scsearch"


def test_get_search_prefix_invalid_raises():
    with pytest.raises(ValueError, match="Unknown search provider 'fakeprovider'"):
        get_search_prefix("fakeprovider")


def test_get_search_prefix_error_lists_valid_providers():
    with pytest.raises(ValueError, match="youtube"):
        get_search_prefix("nope")


def test_provider_names_returns_sorted_list():
    names = provider_names()
    assert names == sorted(names)
    assert "youtube" in names
    assert "soundcloud" in names
