"""Logic for info metadata command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    write_json: bool = False,
    output_dir: str | None = None,
    cookies: str | None = None,
) -> list[str]:
    """Build yt-dlp argument list for fetching video metadata.

    Default mode dumps JSON to stdout. If write_json=True, writes a
    .info.json file to disk instead.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    if write_json:
        args.extend(["--write-info-json", "--skip-download"])
    else:
        args.extend(["--dump-json", "--skip-download"])

    if output_dir:
        args.extend(["-P", output_dir])

    if cookies:
        args.extend(["--cookies", cookies])

    # URL must be last
    args.append(url)
    return args
