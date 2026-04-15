"""Logic for download audio command — builds yt-dlp argument list."""


AUDIO_FORMATS = ("mp3", "opus", "flac", "wav", "m4a", "aac", "vorbis", "alac")

QUALITY_MAP = {
    "best": "0",
    "high": "2",
    "medium": "5",
    "low": "8",
    "worst": "10",
}


def build_args(
    url: str,
    *,
    format: str = "mp3",
    quality: str = "medium",
    output: str | None = None,
    output_dir: str | None = None,
    cookies: str | None = None,
    embed_metadata: bool = False,
    embed_thumbnail: bool = False,
    no_overwrites: bool = False,
    rate_limit: str | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build yt-dlp argument list for extracting audio.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    # Extract audio flag
    args.append("-x")

    # Audio format
    args.extend(["--audio-format", format])

    # Audio quality
    quality_val = QUALITY_MAP.get(quality, quality)
    args.extend(["--audio-quality", quality_val])

    # Output template
    if output:
        args.extend(["-o", output])
    if output_dir:
        args.extend(["-P", output_dir])

    # Overwrite behavior
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
    if embed_thumbnail:
        args.append("--embed-thumbnail")

    # Rate limit
    if rate_limit:
        args.extend(["-r", rate_limit])

    # Extra args passthrough
    if extra_args:
        args.extend(extra_args)

    # URL must be last
    args.append(url)
    return args
