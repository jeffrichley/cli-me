"""Logic for download video command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    output: str | None = None,
    output_dir: str | None = None,
    format: str | None = None,
    max_height: int | None = None,
    max_filesize: str | None = None,
    cookies: str | None = None,
    no_overwrites: bool = False,
    embed_metadata: bool = False,
    embed_subs: bool = False,
    embed_thumbnail: bool = False,
    embed_chapters: bool = False,
    sponsorblock_remove: str | None = None,
    concurrent_fragments: int | None = None,
    rate_limit: str | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build yt-dlp argument list for downloading a video.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    # Format selection
    if format:
        args.extend(["-f", format])
    elif max_height:
        args.extend(["-f", "bv*+ba/b"])
        args.extend(["-S", f"res:{max_height}"])
    else:
        args.extend(["-f", "bv*+ba/b"])

    # Output template
    if output:
        args.extend(["-o", output])
    if output_dir:
        args.extend(["-P", output_dir])

    # Overwrite behavior — always explicit to avoid interactive prompts
    if no_overwrites:
        args.append("--no-overwrites")
    else:
        args.append("--force-overwrites")

    # Cookies
    if cookies:
        args.extend(["--cookies", cookies])

    # Embedding
    if embed_metadata:
        args.append("--embed-metadata")
    if embed_subs:
        args.append("--embed-subs")
    if embed_thumbnail:
        args.append("--embed-thumbnail")
    if embed_chapters:
        args.append("--embed-chapters")

    # SponsorBlock
    if sponsorblock_remove:
        args.extend(["--sponsorblock-remove", sponsorblock_remove])

    # Performance
    if concurrent_fragments is not None:
        args.extend(["-N", str(concurrent_fragments)])
    if rate_limit:
        args.extend(["-r", rate_limit])

    # File size limit
    if max_filesize:
        args.extend(["--max-filesize", max_filesize])

    # Extra args passthrough
    if extra_args:
        args.extend(extra_args)

    # URL must be last
    args.append(url)
    return args
