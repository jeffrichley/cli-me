"""Logic for batch search command — builds yt-dlp argument list."""


def build_args(
    query: str,
    *,
    max_results: int = 5,
    output: str | None = None,
    output_dir: str | None = None,
    format: str | None = None,
    cookies: str | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build yt-dlp argument list for searching and downloading.

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

    # Overwrite behavior
    args.append("--force-overwrites")

    # Cookies
    if cookies:
        args.extend(["--cookies", cookies])

    # Extra args passthrough
    if extra_args:
        args.extend(extra_args)

    # Search query must be last
    args.append(f"ytsearch{max_results}:{query}")
    return args
