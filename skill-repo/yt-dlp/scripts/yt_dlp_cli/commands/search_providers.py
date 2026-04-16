"""Search provider registry — maps provider names to yt-dlp search prefixes."""

PROVIDERS: dict[str, str] = {
    "youtube": "ytsearch",
    "youtube-music": "ytmsearch",
    "soundcloud": "scsearch",
}


def get_search_prefix(provider: str) -> str:
    """Return the yt-dlp search prefix for a provider name.

    Raises ValueError if the provider is unknown.
    """
    if provider not in PROVIDERS:
        valid = ", ".join(sorted(PROVIDERS))
        raise ValueError(
            f"Unknown search provider '{provider}'. Valid providers: {valid}"
        )
    return PROVIDERS[provider]


def provider_names() -> list[str]:
    """Return sorted list of available provider names."""
    return sorted(PROVIDERS)
