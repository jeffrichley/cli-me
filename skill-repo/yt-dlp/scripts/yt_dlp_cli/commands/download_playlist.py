"""Logic for download playlist command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    output: str | None = None,
    output_dir: str | None = None,
    format: str | None = None,
    items: str | None = None,
    archive: str | None = None,
    cookies: str | None = None,
    no_overwrites: bool = False,
    concurrent_fragments: int | None = None,
    rate_limit: str | None = None,
    sleep_interval: float | None = None,
    max_sleep_interval: float | None = None,
    date_after: str | None = None,
    date_before: str | None = None,
    max_downloads: int | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build yt-dlp argument list for downloading a playlist.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    # Do NOT add --no-playlist (we want the full playlist)
    args.append("--yes-playlist")

    # Format selection
    if format:
        args.extend(["-f", format])
    else:
        args.extend(["-f", "bv*+ba/b"])

    # Output template — default to organized by playlist
    if output:
        args.extend(["-o", output])
    else:
        args.extend(["-o", "%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s"])
    if output_dir:
        args.extend(["-P", output_dir])

    # Playlist item selection
    if items:
        args.extend(["-I", items])

    # Archive file
    if archive:
        args.extend(["--download-archive", archive])

    # Overwrite behavior
    if no_overwrites:
        args.append("--no-overwrites")
    else:
        args.append("--force-overwrites")

    # Cookies
    if cookies:
        args.extend(["--cookies", cookies])

    # Date filters
    if date_after:
        args.extend(["--dateafter", date_after])
    if date_before:
        args.extend(["--datebefore", date_before])

    # Max downloads
    if max_downloads is not None:
        args.extend(["--max-downloads", str(max_downloads)])

    # Performance
    if concurrent_fragments is not None:
        args.extend(["-N", str(concurrent_fragments)])
    if rate_limit is not None:
        args.extend(["-r", rate_limit])

    # Polite downloading
    if sleep_interval is not None:
        args.extend(["--sleep-interval", str(sleep_interval)])
    if max_sleep_interval is not None:
        args.extend(["--max-sleep-interval", str(max_sleep_interval)])

    # Continue on errors for playlists
    args.append("-i")

    # Extra args passthrough
    if extra_args:
        args.extend(extra_args)

    # URL must be last
    args.append(url)
    return args
