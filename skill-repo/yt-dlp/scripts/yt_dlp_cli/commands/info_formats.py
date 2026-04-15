"""Logic for info formats command — builds yt-dlp argument list."""


def build_args(url: str, *, cookies: str | None = None) -> list[str]:
    """Build yt-dlp argument list for listing available formats.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []
    if cookies:
        args.extend(["--cookies", cookies])
    args.extend(["-F", url])
    return args


def build_json_args(url: str, *, cookies: str | None = None) -> list[str]:
    """Build yt-dlp argument list for JSON format output.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []
    if cookies:
        args.extend(["--cookies", cookies])
    args.extend(["-j", url])
    return args
