"""Logic for batch from-file command — builds yt-dlp argument list."""


def build_args(
    file: str,
    *,
    format: str | None = None,
    output: str | None = None,
    output_dir: str | None = None,
    archive: str | None = None,
    cookies: str | None = None,
    concurrent_fragments: int | None = None,
    rate_limit: str | None = None,
    sleep_interval: float | None = None,
    max_sleep_interval: float | None = None,
    max_downloads: int | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build yt-dlp argument list for batch downloading from a URL file.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    # Format selection
    if format:
        args.extend(["-f", format])

    # Output template
    if output:
        args.extend(["-o", output])
    if output_dir:
        args.extend(["-P", output_dir])

    # Archive file
    if archive:
        args.extend(["--download-archive", archive])

    # Overwrite behavior — always force for batch
    args.append("--force-overwrites")

    # Cookies
    if cookies:
        args.extend(["--cookies", cookies])

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

    # Max downloads
    if max_downloads is not None:
        args.extend(["--max-downloads", str(max_downloads)])

    # Continue on errors for batch
    args.append("-i")

    # Extra args passthrough
    if extra_args:
        args.extend(extra_args)

    # Batch file must be last
    args.extend(["-a", file])
    return args
