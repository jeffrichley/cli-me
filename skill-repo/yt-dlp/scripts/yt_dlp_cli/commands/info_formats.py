"""Logic for info formats command — builds yt-dlp argument list."""


def build_args(url: str) -> list[str]:
    """Build yt-dlp argument list for listing available formats.

    Returns the argument list (without the yt-dlp executable).
    """
    return ["-F", url]


def build_json_args(url: str) -> list[str]:
    """Build yt-dlp argument list for JSON format output.

    Returns the argument list (without the yt-dlp executable).
    """
    return ["-j", url]
