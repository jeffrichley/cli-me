"""Logic for info search command — search without downloading."""

from .search_providers import get_search_prefix


def build_args(
    query: str,
    *,
    max_results: int = 5,
    provider: str = "youtube",
    cookies: str | None = None,
) -> list[str]:
    """Build yt-dlp argument list for search-only (no download).

    Returns the argument list (without the yt-dlp executable).
    """
    prefix = get_search_prefix(provider)
    args: list[str] = ["--dump-json", "--no-download"]

    if cookies:
        args.extend(["--cookies", cookies])

    args.append(f"{prefix}{max_results}:{query}")
    return args


def format_pretty(result: dict) -> str:
    """Format a single search result as a human-readable line."""
    title = result.get("title", "Unknown")
    url = result.get("webpage_url", "")
    duration = result.get("duration_string", "?:??")
    uploader = result.get("uploader", "Unknown")
    return f"  {title}\n  {uploader} | {duration}\n  {url}"
