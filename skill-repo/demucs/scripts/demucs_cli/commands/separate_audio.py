"""Logic for separate command — builds demucs argument list."""


def build_args(
    files: list[str],
    *,
    model: str = "htdemucs",
    repo: str | None = None,
    device: str | None = None,
    shifts: int = 1,
    overlap: float | None = None,
    segment: int | None = None,
    no_split: bool = False,
    two_stems: str | None = None,
    format: str | None = None,  # "mp3", "flac", or None (WAV default)
    mp3_bitrate: int | None = None,
    mp3_preset: int | None = None,
    int24: bool = False,
    float32: bool = False,
    clip_mode: str | None = None,
    output: str | None = None,
    jobs: int | None = None,
    verbose: bool = False,
) -> list[str]:
    """Build demucs argument list for audio separation.

    Returns the argument list (without the demucs executable).
    """
    if not files:
        raise ValueError("No input files provided.")

    args: list[str] = []

    # Model selection
    args.extend(["-n", model])
    if repo:
        args.extend(["--repo", repo])

    # Device — only add flag when explicitly set (auto-detect = omit)
    if device is not None:
        args.extend(["-d", device])

    # Processing parameters
    args.extend(["--shifts", str(shifts)])

    if overlap is not None:
        args.extend(["--overlap", str(overlap)])

    if segment is not None:
        args.extend(["--segment", str(segment)])

    if no_split:
        args.append("--no-split")

    # Stem selection
    if two_stems:
        args.extend(["--two-stems", two_stems])

    # Output format — validate known values
    if format is not None and format not in ("mp3", "flac", "wav"):
        raise ValueError(f"Unknown format '{format}'. Valid: mp3, flac, wav")

    if format == "mp3":
        args.append("--mp3")
        if mp3_bitrate is not None:
            args.extend(["--mp3-bitrate", str(mp3_bitrate)])
        if mp3_preset is not None:
            args.extend(["--mp3-preset", str(mp3_preset)])
    elif format == "flac":
        args.append("--flac")

    # Bit depth (WAV only, mutually exclusive — ignored for MP3/FLAC)
    if format not in ("mp3", "flac"):
        if int24:
            args.append("--int24")
        elif float32:
            args.append("--float32")

    # Clipping — validate known values
    if clip_mode is not None:
        if clip_mode not in ("rescale", "clamp"):
            raise ValueError(
                f"Unknown clip_mode '{clip_mode}'. Valid: rescale, clamp"
            )
        args.extend(["--clip-mode", clip_mode])

    # Output directory
    if output:
        args.extend(["-o", output])
    else:
        args.extend(["-o", "separated"])

    # Parallel workers (CPU only)
    if jobs is not None:
        args.extend(["-j", str(jobs)])

    # Verbose
    if verbose:
        args.append("-v")

    # Input files last
    args.extend(files)

    return args
