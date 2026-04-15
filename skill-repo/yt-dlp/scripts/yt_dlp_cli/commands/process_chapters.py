"""Logic for process chapters command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    split: bool = False,
    remove: str | None = None,
    output: str | None = None,
    output_dir: str | None = None,
    format: str | None = None,
    cookies: str | None = None,
) -> list[str]:
    """Build yt-dlp argument list for chapter processing.

    Args:
        url: Video URL.
        split: Split video into separate files per chapter.
        remove: Regex pattern for chapters to remove via --remove-chapters.
        output: Output filename template.
        output_dir: Output directory.
        format: Format selector.
        cookies: Path to cookies file.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = ["--force-overwrites"]

    # Chapter operations
    if split:
        args.append("--split-chapters")
    if remove:
        args.extend(["--remove-chapters", remove])

    # Format selection
    if format:
        args.extend(["-f", format])

    # Output template
    if output:
        args.extend(["-o", output])
    if output_dir:
        args.extend(["-P", output_dir])

    # Cookies
    if cookies:
        args.extend(["--cookies", cookies])

    # URL must be last
    args.append(url)
    return args
