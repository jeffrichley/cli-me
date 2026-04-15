"""Logic for info thumbnails command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    download: bool = False,
    cookies: str | None = None,
    convert: str | None = None,
) -> list[str]:
    """Build yt-dlp argument list for thumbnail listing or downloading.

    Default mode lists available thumbnails. If download=True, downloads
    the thumbnail without the video.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    if download:
        args.extend(["--write-thumbnail", "--skip-download"])
    else:
        args.append("--list-thumbnails")

    if cookies:
        args.extend(["--cookies", cookies])

    if convert:
        args.extend(["--convert-thumbnails", convert])

    # URL must be last
    args.append(url)
    return args
