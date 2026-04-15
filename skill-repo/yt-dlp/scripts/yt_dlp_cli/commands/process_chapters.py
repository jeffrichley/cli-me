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
    no_overwrites: bool = False,
    force_keyframes: bool = False,
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
        no_overwrites: Do not overwrite existing files.
        force_keyframes: Force keyframes at cuts for precise chapter splitting.

    Returns the argument list (without the yt-dlp executable).
    """
    if not split and not remove:
        import typer
        typer.echo("WARNING: No --split or --remove specified. Downloading without chapter processing.", err=True)

    args: list[str] = ["--no-overwrites"] if no_overwrites else ["--force-overwrites"]

    # Force keyframes at cuts
    if force_keyframes:
        args.append("--force-keyframes-at-cuts")

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
