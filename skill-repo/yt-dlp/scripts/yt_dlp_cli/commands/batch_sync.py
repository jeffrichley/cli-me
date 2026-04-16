"""Logic for batch sync command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    archive: str,
    format: str | None = None,
    output: str | None = None,
    output_dir: str | None = None,
    cookies: str | None = None,
    break_on_existing: bool = False,
    sleep_interval: float | None = None,
    max_sleep_interval: float | None = None,
    max_downloads: int | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build yt-dlp argument list for incremental sync with an archive.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    # Archive file — core to sync
    args.extend(["--download-archive", archive])

    # Format selection
    if format:
        args.extend(["-f", format])

    # Output template
    if output:
        args.extend(["-o", output])
    if output_dir:
        args.extend(["-P", output_dir])

    # Overwrite behavior — always force for sync
    args.append("--force-overwrites")

    # Break on existing — stop early when hitting already-downloaded videos
    if break_on_existing:
        args.append("--break-on-existing")

    # Cookies
    if cookies:
        args.extend(["--cookies", cookies])

    # Polite downloading
    if sleep_interval is not None:
        args.extend(["--sleep-interval", str(sleep_interval)])
    if max_sleep_interval is not None:
        args.extend(["--max-sleep-interval", str(max_sleep_interval)])

    # Max downloads
    if max_downloads is not None:
        args.extend(["--max-downloads", str(max_downloads)])

    # Continue on errors
    args.append("-i")

    # Extra args passthrough
    if extra_args:
        args.extend(extra_args)

    # URL must be last
    args.append(url)
    return args
