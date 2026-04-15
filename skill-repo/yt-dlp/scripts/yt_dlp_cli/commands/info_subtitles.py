"""Logic for info subtitles command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    download: bool = False,
    auto_subs: bool = False,
    langs: str | None = None,
    format: str | None = None,
    cookies: str | None = None,
) -> list[str]:
    """Build yt-dlp argument list for subtitle listing or downloading.

    Default mode lists available subtitles. If download=True, downloads
    subtitle files without the video.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    if download:
        args.extend(["--write-subs", "--skip-download"])
        if auto_subs:
            args.append("--write-auto-subs")
    else:
        args.append("--list-subs")

    if langs:
        args.extend(["--sub-langs", langs])

    if format:
        args.extend(["--sub-format", format])

    if cookies:
        args.extend(["--cookies", cookies])

    # URL must be last
    args.append(url)
    return args
