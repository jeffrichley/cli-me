"""Logic for config archive commands — builds yt-dlp argument lists."""


def build_check_args(archive_file: str, url: str) -> list[str]:
    """Build yt-dlp argument list for checking if a URL is in an archive.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    args.extend(["--download-archive", archive_file])
    args.append("--simulate")
    args.extend(["--print", "%(id)s"])

    # URL must be last
    args.append(url)
    return args


def build_add_args(archive_file: str, url: str) -> list[str]:
    """Build yt-dlp argument list for adding a URL to an archive without downloading.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    args.extend(["--download-archive", archive_file])
    args.append("--simulate")
    args.append("--force-write-archive")

    # URL must be last
    args.append(url)
    return args
