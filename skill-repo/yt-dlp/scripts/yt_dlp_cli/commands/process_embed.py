"""Logic for process embed command — builds yt-dlp argument list."""


def build_args(
    url: str,
    *,
    subs: bool = False,
    thumbnail: bool = False,
    metadata: bool = False,
    chapters: bool = False,
    info_json: bool = False,
    output: str | None = None,
    output_dir: str | None = None,
    format: str | None = None,
    sub_langs: str | None = None,
    cookies: str | None = None,
    no_overwrites: bool = False,
) -> list[str]:
    """Build yt-dlp argument list for embedding metadata into downloads.

    Args:
        url: Video URL.
        subs: Embed subtitles.
        thumbnail: Embed thumbnail.
        metadata: Embed metadata tags.
        chapters: Embed chapter markers.
        info_json: Embed info.json.
        output: Output filename template.
        output_dir: Output directory.
        format: Format selector.
        sub_langs: Subtitle languages to download (e.g., 'en,es', 'all').
        cookies: Path to cookies file.
        no_overwrites: Do not overwrite existing files.

    Returns the argument list (without the yt-dlp executable).
    """
    if not any([subs, thumbnail, metadata, chapters, info_json]):
        import typer
        typer.echo("WARNING: No embed flags specified. Downloading without embedding anything.", err=True)

    args: list[str] = ["--no-overwrites"] if no_overwrites else ["--force-overwrites"]

    # Embed flags
    if subs:
        args.append("--embed-subs")
    if thumbnail:
        args.append("--embed-thumbnail")
    if metadata:
        args.append("--embed-metadata")
    if chapters:
        args.append("--embed-chapters")
    if info_json:
        args.append("--embed-info-json")

    # Subtitle languages (useful when embedding subs)
    if sub_langs:
        args.extend(["--sub-langs", sub_langs])

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
