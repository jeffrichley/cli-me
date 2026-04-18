# yt-dlp Search Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-provider search support and a search-only (no download) command to the yt-dlp skill.

**Architecture:** A shared `search_providers.py` module defines the provider map (provider name -> yt-dlp search prefix). Both the existing `batch search` command and a new `info search` command use this map via a `--provider` flag (default: `youtube`). The new `info search` command uses `--dump-json --no-download` to return results without downloading, outputting JSON by default with a `--pretty` flag for human-readable output.

**Tech Stack:** Python 3.12+, typer, rich, yt-dlp

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `commands/search_providers.py` | Create | Provider name -> yt-dlp prefix map, validation, listing |
| `commands/info_search.py` | Create | Build args for search-only (no download) |
| `commands/batch_search.py` | Modify | Accept provider param, use shared map |
| `info.py` | Modify | Add `search` subcommand |
| `batch.py` | Modify | Add `--provider` option to existing `search` command |

All paths relative to `skill-repo/yt-dlp/scripts/yt_dlp_cli/`.

Tests live at `skill-repo/yt-dlp/tests/` (new directory).

---

### Task 1: Create the shared search providers module

**Files:**
- Create: `skill-repo/yt-dlp/tests/__init__.py`
- Create: `skill-repo/yt-dlp/tests/test_search_providers.py`
- Create: `skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/search_providers.py`

- [ ] **Step 1: Create test directory and write failing tests**

Create `skill-repo/yt-dlp/tests/__init__.py` (empty).

Create `skill-repo/yt-dlp/tests/test_search_providers.py`:

```python
"""Tests for the search providers module."""

from yt_dlp_cli.commands.search_providers import (
    PROVIDERS,
    get_search_prefix,
    provider_names,
)
import pytest


def test_providers_map_has_youtube():
    assert "youtube" in PROVIDERS
    assert PROVIDERS["youtube"] == "ytsearch"


def test_providers_map_has_soundcloud():
    assert "soundcloud" in PROVIDERS
    assert PROVIDERS["soundcloud"] == "scsearch"


def test_providers_map_has_youtube_music():
    assert "youtube-music" in PROVIDERS
    assert PROVIDERS["youtube-music"] == "ytmsearch"


def test_providers_map_has_youtube_videos():
    assert "youtube-videos" in PROVIDERS
    assert PROVIDERS["youtube-videos"] == "yvsearch"


def test_get_search_prefix_valid():
    assert get_search_prefix("youtube") == "ytsearch"
    assert get_search_prefix("soundcloud") == "scsearch"


def test_get_search_prefix_invalid_raises():
    with pytest.raises(ValueError, match="Unknown search provider 'fakeprovider'"):
        get_search_prefix("fakeprovider")


def test_get_search_prefix_error_lists_valid_providers():
    with pytest.raises(ValueError, match="youtube"):
        get_search_prefix("nope")


def test_provider_names_returns_sorted_list():
    names = provider_names()
    assert names == sorted(names)
    assert "youtube" in names
    assert "soundcloud" in names
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `skill-repo/yt-dlp/scripts/`:

```bash
cd skill-repo/yt-dlp/scripts && uv run python -m pytest ../tests/test_search_providers.py -v
```

Expected: FAIL — `ModuleNotFoundError` or `ImportError` because `search_providers` doesn't exist yet.

- [ ] **Step 3: Implement the search providers module**

Create `skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/search_providers.py`:

```python
"""Search provider registry — maps provider names to yt-dlp search prefixes."""

PROVIDERS: dict[str, str] = {
    "youtube": "ytsearch",
    "youtube-music": "ytmsearch",
    "youtube-videos": "yvsearch",
    "soundcloud": "scsearch",
}


def get_search_prefix(provider: str) -> str:
    """Return the yt-dlp search prefix for a provider name.

    Raises ValueError if the provider is unknown.
    """
    if provider not in PROVIDERS:
        valid = ", ".join(sorted(PROVIDERS))
        raise ValueError(
            f"Unknown search provider '{provider}'. Valid providers: {valid}"
        )
    return PROVIDERS[provider]


def provider_names() -> list[str]:
    """Return sorted list of available provider names."""
    return sorted(PROVIDERS)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd skill-repo/yt-dlp/scripts && uv run python -m pytest ../tests/test_search_providers.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skill-repo/yt-dlp/tests/ skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/search_providers.py
git commit -m "feat(yt-dlp): add search providers registry"
```

---

### Task 2: Add --provider flag to batch search

**Files:**
- Create: `skill-repo/yt-dlp/tests/test_batch_search.py`
- Modify: `skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/batch_search.py`
- Modify: `skill-repo/yt-dlp/scripts/yt_dlp_cli/batch.py`

- [ ] **Step 1: Write failing tests**

Create `skill-repo/yt-dlp/tests/test_batch_search.py`:

```python
"""Tests for batch search command arg building."""

from yt_dlp_cli.commands.batch_search import build_args


def test_default_provider_is_youtube():
    args = build_args("test query", max_results=3)
    assert "ytsearch3:test query" in args


def test_soundcloud_provider():
    args = build_args("test query", max_results=5, provider="soundcloud")
    assert "scsearch5:test query" in args


def test_youtube_music_provider():
    args = build_args("test query", max_results=2, provider="youtube-music")
    assert "ytmsearch2:test query" in args


def test_invalid_provider_raises():
    import pytest
    with pytest.raises(ValueError, match="Unknown search provider"):
        build_args("test query", provider="fakeprovider")


def test_search_query_is_last_arg():
    args = build_args("test query", format="bestaudio", provider="youtube")
    assert args[-1] == "ytsearch5:test query"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd skill-repo/yt-dlp/scripts && uv run python -m pytest ../tests/test_batch_search.py -v
```

Expected: FAIL — `build_args()` doesn't accept `provider` parameter yet.

- [ ] **Step 3: Update batch_search.py to accept provider**

Replace `skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/batch_search.py`:

```python
"""Logic for batch search command — builds yt-dlp argument list."""

from .search_providers import get_search_prefix


def build_args(
    query: str,
    *,
    max_results: int = 5,
    provider: str = "youtube",
    output: str | None = None,
    output_dir: str | None = None,
    format: str | None = None,
    cookies: str | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build yt-dlp argument list for searching and downloading.

    Returns the argument list (without the yt-dlp executable).
    """
    prefix = get_search_prefix(provider)
    args: list[str] = []

    # Format selection
    if format:
        args.extend(["-f", format])

    # Output template
    if output:
        args.extend(["-o", output])
    if output_dir:
        args.extend(["-P", output_dir])

    # Overwrite behavior
    args.append("--force-overwrites")

    # Cookies
    if cookies:
        args.extend(["--cookies", cookies])

    # Extra args passthrough
    if extra_args:
        args.extend(extra_args)

    # Search query must be last
    args.append(f"{prefix}{max_results}:{query}")
    return args
```

- [ ] **Step 4: Update batch.py to expose --provider option**

In `skill-repo/yt-dlp/scripts/yt_dlp_cli/batch.py`, update the `search` command:

Add `provider_names` import at the top (alongside existing imports):
```python
from .commands.search_providers import provider_names
```

Update the `search` function signature and body:

```python
@batch_app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    max_results: Annotated[int, typer.Option(help="Maximum number of results")] = 5,
    provider: Annotated[str, typer.Option(help=f"Search provider ({', '.join(provider_names())})")] = "youtube",
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output filename template")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-P", help="Output directory")] = None,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Format selector")] = None,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
) -> None:
    """Search and download the results."""
    args = batch_search.build_args(
        query,
        max_results=max_results,
        provider=provider,
        output=output,
        output_dir=output_dir,
        format=format,
        cookies=cookies,
    )
    run_command(args)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd skill-repo/yt-dlp/scripts && uv run python -m pytest ../tests/test_batch_search.py ../tests/test_search_providers.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/batch_search.py skill-repo/yt-dlp/scripts/yt_dlp_cli/batch.py skill-repo/yt-dlp/tests/test_batch_search.py
git commit -m "feat(yt-dlp): add --provider flag to batch search"
```

---

### Task 3: Create the info search command (search-only, no download)

**Files:**
- Create: `skill-repo/yt-dlp/tests/test_info_search.py`
- Create: `skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/info_search.py`
- Modify: `skill-repo/yt-dlp/scripts/yt_dlp_cli/info.py`

- [ ] **Step 1: Write failing tests**

Create `skill-repo/yt-dlp/tests/test_info_search.py`:

```python
"""Tests for info search command arg building."""

import json
from yt_dlp_cli.commands.info_search import build_args, format_pretty


def test_default_args_include_no_download():
    args = build_args("test query")
    assert "--dump-json" in args
    assert "--no-download" in args


def test_default_provider_is_youtube():
    args = build_args("test query", max_results=3)
    assert "ytsearch3:test query" in args


def test_soundcloud_provider():
    args = build_args("test query", provider="soundcloud", max_results=2)
    assert "scsearch2:test query" in args


def test_does_not_include_force_overwrites():
    args = build_args("test query")
    assert "--force-overwrites" not in args


def test_cookies_passed_through():
    args = build_args("test query", cookies="/tmp/cookies.txt")
    assert "--cookies" in args
    assert "/tmp/cookies.txt" in args


def test_search_query_is_last():
    args = build_args("test query", cookies="/tmp/c.txt")
    assert args[-1] == "ytsearch5:test query"


def test_format_pretty_single_result():
    result = {
        "title": "My Video",
        "webpage_url": "https://example.com/watch?v=abc",
        "duration_string": "3:45",
        "uploader": "SomeChannel",
    }
    output = format_pretty(result)
    assert "My Video" in output
    assert "https://example.com/watch?v=abc" in output
    assert "3:45" in output
    assert "SomeChannel" in output


def test_format_pretty_missing_fields():
    result = {"title": "Minimal"}
    output = format_pretty(result)
    assert "Minimal" in output
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd skill-repo/yt-dlp/scripts && uv run python -m pytest ../tests/test_info_search.py -v
```

Expected: FAIL — `info_search` module doesn't exist.

- [ ] **Step 3: Implement info_search.py**

Create `skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/info_search.py`:

```python
"""Logic for info search command — search without downloading."""

from .search_providers import get_search_prefix


def build_args(
    query: str,
    *,
    max_results: int = 5,
    provider: str = "youtube",
    cookies: str | None = None,
) -> list[str]:
    """Build yt-dlp argument list for search-only (no download).

    Returns the argument list (without the yt-dlp executable).
    """
    prefix = get_search_prefix(provider)
    args: list[str] = ["--dump-json", "--no-download"]

    if cookies:
        args.extend(["--cookies", cookies])

    args.append(f"{prefix}{max_results}:{query}")
    return args


def format_pretty(result: dict) -> str:
    """Format a single search result as a human-readable line."""
    title = result.get("title", "Unknown")
    url = result.get("webpage_url", "")
    duration = result.get("duration_string", "?:??")
    uploader = result.get("uploader", "Unknown")
    return f"  {title}\n  {uploader} | {duration}\n  {url}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd skill-repo/yt-dlp/scripts && uv run python -m pytest ../tests/test_info_search.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Wire up info search in info.py**

In `skill-repo/yt-dlp/scripts/yt_dlp_cli/info.py`, add the import and command:

Add to imports:
```python
from .commands import info_formats, info_metadata, info_subtitles, info_thumbnails, info_search
from .commands.search_providers import provider_names
```

Add new command at the end of the file:

```python
@info_app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    max_results: Annotated[int, typer.Option(help="Maximum number of results")] = 5,
    provider: Annotated[str, typer.Option(help=f"Search provider ({', '.join(provider_names())})")] = "youtube",
    pretty: Annotated[bool, typer.Option("--pretty", help="Human-readable output instead of JSON")] = False,
    cookies: Annotated[Optional[str], typer.Option(help="Path to cookies file")] = None,
) -> None:
    """Search for videos without downloading. Outputs JSON by default."""
    import json

    args = info_search.build_args(
        query,
        max_results=max_results,
        provider=provider,
        cookies=cookies,
    )
    result = run_command(args, capture=True)

    # yt-dlp --dump-json outputs one JSON object per line
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    results = [json.loads(line) for line in lines]

    if pretty:
        for i, item in enumerate(results, 1):
            typer.echo(f"\n[{i}] {info_search.format_pretty(item)}")
    else:
        typer.echo(json.dumps(results, indent=2))
```

- [ ] **Step 6: Run all tests**

```bash
cd skill-repo/yt-dlp/scripts && uv run python -m pytest ../tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/info_search.py skill-repo/yt-dlp/scripts/yt_dlp_cli/info.py skill-repo/yt-dlp/tests/test_info_search.py
git commit -m "feat(yt-dlp): add info search command with --provider and --pretty"
```

---

### Task 4: Update SKILL.md and smoke test

**Files:**
- Modify: `skill-repo/yt-dlp/SKILL.md`

- [ ] **Step 1: Update SKILL.md command reference**

Add `info search` to the info command group section and update `batch search` to mention the `--provider` flag. Read the current SKILL.md first to find the exact sections to update.

Key additions:
- `info search <query>` — search without downloading, JSON output by default, `--pretty` for human-readable, `--provider` to pick source
- `batch search` — note the new `--provider` flag
- Document available providers: youtube (default), youtube-music, youtube-videos, soundcloud

- [ ] **Step 2: Smoke test — verify CLI help shows new commands**

```bash
cd skill-repo/yt-dlp/scripts && uv run python -m yt_dlp_cli info search --help
```

Expected: Shows help with `--provider`, `--pretty`, `--max-results`, `--cookies` options.

```bash
cd skill-repo/yt-dlp/scripts && uv run python -m yt_dlp_cli batch search --help
```

Expected: Shows help with `--provider` option added.

- [ ] **Step 3: Commit**

```bash
git add skill-repo/yt-dlp/SKILL.md
git commit -m "docs(yt-dlp): update SKILL.md with search provider and info search"
```
