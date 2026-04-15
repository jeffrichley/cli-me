"""Logic for download channel command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    output: str | None = None,
    output_dir: str | None = None,
    format: str | None = None,
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
    break_on_existing: bool = False,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build yt-dlp argument list for downloading a channel.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    # Format selection
    if format:
        args.extend(["-f", format])
    else:
        args.extend(["-f", "bv*+ba/b"])

    # Output template — default to organized by channel
    if output:
        args.extend(["-o", output])
    else:
        args.extend(["-o", "%(channel)s/%(upload_date)s - %(title)s.%(ext)s"])
    if output_dir:
        args.extend(["-P", output_dir])

    # Archive file — essential for channels
    if archive:
        args.extend(["--download-archive", archive])

    # Break on existing — stop when hitting already-downloaded videos
    if break_on_existing:
        args.append("--break-on-existing")

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
    if max_downloads:
        args.extend(["--max-downloads", str(max_downloads)])

    # Performance
    if concurrent_fragments:
        args.extend(["-N", str(concurrent_fragments)])
    if rate_limit:
        args.extend(["-r", rate_limit])

    # Polite downloading
    if sleep_interval:
        args.extend(["--sleep-interval", str(sleep_interval)])
    if max_sleep_interval:
        args.extend(["--max-sleep-interval", str(max_sleep_interval)])

    # Continue on errors for channels
    args.append("-i")

    # Extra args passthrough
    if extra_args:
        args.extend(extra_args)

    # URL must be last
    args.append(url)
    return args
