"""Logic for process remux command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    container: str = "mp4",
    format: str | None = None,
    output: str | None = None,
    output_dir: str | None = None,
    cookies: str | None = None,
    no_overwrites: bool = False,
) -> list[str]:
    """Build yt-dlp argument list for remuxing video to a different container.

    Args:
        url: Video URL.
        container: Target container format (e.g., mp4, mkv, webm).
        format: Format selector.
        output: Output filename template.
        output_dir: Output directory.
        cookies: Path to cookies file.
        no_overwrites: Do not overwrite existing files.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = ["--no-overwrites"] if no_overwrites else ["--force-overwrites"]

    # Remux to target container
    args.extend(["--remux-video", container])

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
