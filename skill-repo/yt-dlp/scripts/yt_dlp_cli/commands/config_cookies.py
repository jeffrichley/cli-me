"""Logic for config cookies command — builds yt-dlp argument list."""


def build_args(
    *,
    browser: str,
    output: str = "cookies.txt",
    profile: str | None = None,
    keyring: str | None = None,
    container: str | None = None,
) -> list[str]:
    """Build yt-dlp argument list for extracting cookies from a browser.

    Returns the argument list (without the yt-dlp executable).
    """
    args: list[str] = []

    # Build the browser spec: BROWSER[+KEYRING][:PROFILE][::CONTAINER]
    browser_spec = browser
    if keyring:
        browser_spec += f"+{keyring}"
    if profile:
        browser_spec += f":{profile}"
    if container:
        browser_spec += f"::{container}"

    args.extend(["--cookies-from-browser", browser_spec])

    # Output cookies file
    args.extend(["--cookies", output])

    # Skip actual downloading — we just want the cookies
    args.append("--skip-download")

    # Force overwrites on the cookie file
    args.append("--force-overwrites")

    # Dummy URL — yt-dlp requires a URL argument
    args.append("https://www.youtube.com/")
    return args
