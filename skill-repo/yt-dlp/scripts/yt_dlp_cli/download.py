"""Download command group — core downloading with format selection."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import run_command
from .commands import download_video, download_audio, download_playlist, download_channel

download_app = typer.Typer(help="Download video/audio from URLs.", no_args_is_help=True)
app.add_typer(download_app, name="download")


@download_app.command()
def video(
    url: Annotated[str, typer.Argument(help="URL to download")],
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector (e.g., '22', 'bv*+ba/b')")] = None,
    max_height: Annotated[Optional[int], typer.Option(help="Max video height (e.g., 720, 1080)")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    no_overwrites: Annotated[bool, typer.Option(help="Never overwrite existing files")] = False,
    embed_metadata: Annotated[bool, typer.Option(help="Embed metadata tags")] = False,
    embed_subs: Annotated[bool, typer.Option(help="Embed subtitles")] = False,
    embed_thumbnail: Annotated[bool, typer.Option(help="Embed thumbnail")] = False,
    embed_chapters: Annotated[bool, typer.Option(help="Embed chapter markers")] = False,
    sponsorblock_remove: Annotated[Optional[str], typer.Option(help="SponsorBlock categories to remove (comma-separated)")] = None,
    concurrent_fragments: Annotated[Optional[int], typer.Option("--concurrent-fragments", "-N", help="Concurrent fragment downloads")] = None,
    rate_limit: Annotated[Optional[str], typer.Option("--rate-limit", "-r", help="Rate limit (e.g., '50K', '1M')")] = None,
    max_filesize: Annotated[Optional[str], typer.Option(help="Skip files larger than (e.g., '100M')")] = None,
) -> None:
    """Download a video from a URL."""
    args = download_video.build_args(
        url,
        format=format,
        max_height=max_height,
        output=output,
        output_dir=output_dir,
        cookies=cookies,
        no_overwrites=no_overwrites,
        embed_metadata=embed_metadata,
        embed_subs=embed_subs,
        embed_thumbnail=embed_thumbnail,
        embed_chapters=embed_chapters,
        sponsorblock_remove=sponsorblock_remove,
        concurrent_fragments=concurrent_fragments,
        rate_limit=rate_limit,
        max_filesize=max_filesize,
    )
    run_command(args)


@download_app.command()
def audio(
    url: Annotated[str, typer.Argument(help="URL to extract audio from")],
    format: Annotated[str, typer.Option("--format", "-f", help="Audio format: mp3, opus, flac, wav, m4a, aac, vorbis, alac")] = "mp3",
    quality: Annotated[str, typer.Option("--quality", "-q", help="Audio quality: best, high, medium, low, worst, or kbps value")] = "medium",
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    no_overwrites: Annotated[bool, typer.Option(help="Never overwrite existing files")] = False,
    embed_metadata: Annotated[bool, typer.Option(help="Embed metadata tags")] = False,
    embed_thumbnail: Annotated[bool, typer.Option(help="Embed thumbnail as cover art")] = False,
    rate_limit: Annotated[Optional[str], typer.Option("--rate-limit", "-r", help="Rate limit (e.g., '50K', '1M')")] = None,
) -> None:
    """Download and extract audio from a URL."""
    args = download_audio.build_args(
        url,
        format=format,
        quality=quality,
        output=output,
        output_dir=output_dir,
        cookies=cookies,
        no_overwrites=no_overwrites,
        embed_metadata=embed_metadata,
        embed_thumbnail=embed_thumbnail,
        rate_limit=rate_limit,
    )
    run_command(args)


@download_app.command()
def playlist(
    url: Annotated[str, typer.Argument(help="Playlist URL to download")],
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector")] = None,
    items: Annotated[Optional[str], typer.Option("--items", "-I", help="Playlist items to download (e.g., '1:5', '2,4,6')")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    archive: Annotated[Optional[str], typer.Option(help="Archive file to track downloaded videos")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    no_overwrites: Annotated[bool, typer.Option(help="Never overwrite existing files")] = False,
    concurrent_fragments: Annotated[Optional[int], typer.Option("--concurrent-fragments", "-N", help="Concurrent fragment downloads")] = None,
    rate_limit: Annotated[Optional[str], typer.Option("--rate-limit", "-r", help="Rate limit")] = None,
    sleep_interval: Annotated[Optional[float], typer.Option(help="Sleep seconds between downloads")] = None,
    max_sleep_interval: Annotated[Optional[float], typer.Option(help="Max random sleep seconds")] = None,
    date_after: Annotated[Optional[str], typer.Option(help="Only videos uploaded after date (YYYYMMDD)")] = None,
    date_before: Annotated[Optional[str], typer.Option(help="Only videos uploaded before date (YYYYMMDD)")] = None,
    max_downloads: Annotated[Optional[int], typer.Option(help="Stop after N downloads")] = None,
) -> None:
    """Download all videos from a playlist."""
    args = download_playlist.build_args(
        url,
        format=format,
        items=items,
        output=output,
        output_dir=output_dir,
        archive=archive,
        cookies=cookies,
        no_overwrites=no_overwrites,
        concurrent_fragments=concurrent_fragments,
        rate_limit=rate_limit,
        sleep_interval=sleep_interval,
        max_sleep_interval=max_sleep_interval,
        date_after=date_after,
        date_before=date_before,
        max_downloads=max_downloads,
    )
    run_command(args)


@download_app.command()
def channel(
    url: Annotated[str, typer.Argument(help="Channel URL to download")],
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    archive: Annotated[Optional[str], typer.Option(help="Archive file to track downloaded videos")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    no_overwrites: Annotated[bool, typer.Option(help="Never overwrite existing files")] = False,
    break_on_existing: Annotated[bool, typer.Option(help="Stop on already-downloaded video")] = False,
    concurrent_fragments: Annotated[Optional[int], typer.Option("--concurrent-fragments", "-N", help="Concurrent fragment downloads")] = None,
    rate_limit: Annotated[Optional[str], typer.Option("--rate-limit", "-r", help="Rate limit")] = None,
    sleep_interval: Annotated[Optional[float], typer.Option(help="Sleep seconds between downloads")] = None,
    max_sleep_interval: Annotated[Optional[float], typer.Option(help="Max random sleep seconds")] = None,
    date_after: Annotated[Optional[str], typer.Option(help="Only videos uploaded after date (YYYYMMDD)")] = None,
    date_before: Annotated[Optional[str], typer.Option(help="Only videos uploaded before date (YYYYMMDD)")] = None,
    max_downloads: Annotated[Optional[int], typer.Option(help="Stop after N downloads")] = None,
) -> None:
    """Download all videos from a channel."""
    args = download_channel.build_args(
        url,
        format=format,
        output=output,
        output_dir=output_dir,
        archive=archive,
        cookies=cookies,
        no_overwrites=no_overwrites,
        break_on_existing=break_on_existing,
        concurrent_fragments=concurrent_fragments,
        rate_limit=rate_limit,
        sleep_interval=sleep_interval,
        max_sleep_interval=max_sleep_interval,
        date_after=date_after,
        date_before=date_before,
        max_downloads=max_downloads,
    )
    run_command(args)
