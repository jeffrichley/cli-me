"""Process command group — post-processing operations."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import run_command
from .commands import process_sponsorblock, process_chapters, process_remux, process_embed

process_app = typer.Typer(help="Post-process downloads: SponsorBlock, chapters, remux, embed.", no_args_is_help=True)
app.add_typer(process_app, name="process")


@process_app.command()
def sponsorblock(
    url: Annotated[str, typer.Argument(help="URL to process")],
    remove: Annotated[Optional[str], typer.Option(help="SponsorBlock categories to remove (comma-separated: sponsor, selfpromo, interaction, intro, outro, preview, music_offtopic, filler, all)")] = None,
    mark: Annotated[Optional[str], typer.Option(help="SponsorBlock categories to mark as chapters instead of removing")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    force_keyframes: Annotated[bool, typer.Option(help="Force keyframes at cuts for precise removal")] = False,
    no_overwrites: Annotated[bool, typer.Option(help="Do not overwrite existing files")] = False,
) -> None:
    """Remove or mark SponsorBlock segments in a video."""
    args = process_sponsorblock.build_args(
        url,
        remove=remove,
        mark=mark,
        output=output,
        output_dir=output_dir,
        format=format,
        cookies=cookies,
        force_keyframes=force_keyframes,
        no_overwrites=no_overwrites,
    )
    run_command(args)


@process_app.command()
def chapters(
    url: Annotated[str, typer.Argument(help="URL to process")],
    split: Annotated[bool, typer.Option(help="Split video into separate files per chapter")] = False,
    remove: Annotated[Optional[str], typer.Option(help="Regex pattern for chapters to remove")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    no_overwrites: Annotated[bool, typer.Option(help="Do not overwrite existing files")] = False,
    force_keyframes: Annotated[bool, typer.Option(help="Force keyframes at cuts for precise chapter splitting")] = False,
) -> None:
    """Split or remove chapters from a video."""
    args = process_chapters.build_args(
        url,
        split=split,
        remove=remove,
        output=output,
        output_dir=output_dir,
        format=format,
        cookies=cookies,
        no_overwrites=no_overwrites,
        force_keyframes=force_keyframes,
    )
    run_command(args)


@process_app.command()
def remux(
    url: Annotated[str, typer.Argument(help="URL to process")],
    container: Annotated[str, typer.Option(help="Target container format (e.g., mp4, mkv, webm)")] = "mp4",
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    no_overwrites: Annotated[bool, typer.Option(help="Do not overwrite existing files")] = False,
) -> None:
    """Remux video into a different container format."""
    args = process_remux.build_args(
        url,
        container=container,
        format=format,
        output=output,
        output_dir=output_dir,
        cookies=cookies,
        no_overwrites=no_overwrites,
    )
    run_command(args)


@process_app.command()
def embed(
    url: Annotated[str, typer.Argument(help="URL to process")],
    subs: Annotated[bool, typer.Option(help="Embed subtitles")] = False,
    thumbnail: Annotated[bool, typer.Option(help="Embed thumbnail")] = False,
    metadata: Annotated[bool, typer.Option(help="Embed metadata tags")] = False,
    chapters: Annotated[bool, typer.Option(help="Embed chapter markers")] = False,
    info_json: Annotated[bool, typer.Option(help="Embed info.json")] = False,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector")] = None,
    sub_langs: Annotated[Optional[str], typer.Option(help="Subtitle languages to download (e.g., 'en,es', 'all')")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
    no_overwrites: Annotated[bool, typer.Option(help="Do not overwrite existing files")] = False,
) -> None:
    """Embed metadata, subtitles, thumbnails, or chapters into a download."""
    args = process_embed.build_args(
        url,
        subs=subs,
        thumbnail=thumbnail,
        metadata=metadata,
        chapters=chapters,
        info_json=info_json,
        output=output,
        output_dir=output_dir,
        format=format,
        sub_langs=sub_langs,
        cookies=cookies,
        no_overwrites=no_overwrites,
    )
    run_command(args)
