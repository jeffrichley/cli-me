"""Logic for process sponsorblock command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    remove: str | None = None,
    mark: str | None = None,
    output: str | None = None,
    output_dir: str | None = None,
    format: str | None = None,
    cookies: str | None = None,
    force_keyframes: bool = False,
) -> list[str]:
    """Build yt-dlp argument list for SponsorBlock processing.

    Args:
        url: Video URL.
        remove: Comma-separated SponsorBlock categories to remove
            (sponsor, selfpromo, interaction, intro, outro, preview,
            music_offtopic, filler, all).
        mark: Comma-separated categories to mark as chapters instead of removing.
        output: Output filename template.
        output_dir: Output directory.
        format: Format selector.
        cookies: Path to cookies file.
        force_keyframes: Force keyframes at cuts for precise removal.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = ["--force-overwrites"]

    # SponsorBlock actions
    if remove:
        args.extend(["--sponsorblock-remove", remove])
    if mark:
        args.extend(["--sponsorblock-mark", mark])

    # Force keyframes at cuts
    if force_keyframes:
        args.append("--force-keyframes-at-cuts")

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
