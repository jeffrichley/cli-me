# yt-dlp Adversarial Review Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 15 objective failures and address the 14 judgment calls from the adversarial review.

**Architecture:** Fixes grouped by severity and file proximity. Critical bugs first, then documentation alignment, then test hardening.

**Tech Stack:** Python (Typer CLI), Markdown wiki pages, pytest

---

### Task 1: Fix critical CLI invocation (R2 — BLOCKING)

SKILL.md tells agents to run `uv run yt_dlp_cli` but there's no top-level
script file. Only `uv run python -m yt_dlp_cli` works from within `scripts/`.

**Files:**
- Create: `skill-repo/yt-dlp/scripts/yt_dlp_cli.py`
- Modify: `skill-repo/yt-dlp/SKILL.md`

- [ ] **Step 1: Create the shim script**

Create `skill-repo/yt-dlp/scripts/yt_dlp_cli.py` (matches the ffmpeg pattern):

```python
"""Entry point for uv run yt_dlp_cli.py"""

from yt_dlp_cli import app

if __name__ == "__main__":
    app()
else:
    app()
```

- [ ] **Step 2: Verify the shim works**

```bash
cd skill-repo/yt-dlp/scripts
uv run yt_dlp_cli.py --help
uv run yt_dlp_cli.py download --help
```

Expected: Both show help output with all commands.

- [ ] **Step 3: Verify it works from outside the directory**

```bash
uv run --project skill-repo/yt-dlp/scripts skill-repo/yt-dlp/scripts/yt_dlp_cli.py --help
```

Expected: Shows help output.

- [ ] **Step 4: Update SKILL.md invocation instructions**

Read `skill-repo/yt-dlp/SKILL.md`. Replace the CLI Commands section invocation
patterns to use `yt_dlp_cli.py` instead of `yt_dlp_cli`:

Change:
```
uv run yt_dlp_cli <group> <command> [options]
```
To:
```
uv run yt_dlp_cli.py <group> <command> [options]
```

And:
```
uv run --project <skill-dir>/scripts <skill-dir>/scripts/yt_dlp_cli <group> <command> [options]
```
To:
```
uv run --project <skill-dir>/scripts <skill-dir>/scripts/yt_dlp_cli.py <group> <command> [options]
```

Also update the help command pattern and all Quick Examples to use `yt_dlp_cli.py`.

- [ ] **Step 5: Commit**

```bash
git add skill-repo/yt-dlp/scripts/yt_dlp_cli.py skill-repo/yt-dlp/SKILL.md
git commit -m "fix(yt-dlp): add shim script so CLI is invocable as documented"
```

---

### Task 2: Fix config_cookies browser spec bug (R3 — BUG)

The browser spec construction uses `:` for all separators but yt-dlp expects
`+` for keyring and `::` for container.

Correct format: `BROWSER[+KEYRING][:PROFILE][::CONTAINER]`

**Files:**
- Modify: `skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/config_cookies.py`
- Modify: `qa/yt-dlp/test_batch_config_commands.py`

- [ ] **Step 1: Write failing tests for the correct browser spec format**

Read `qa/yt-dlp/test_batch_config_commands.py`. Add these tests to
`TestConfigCookies`:

```python
def test_keyring_uses_plus_prefix(self):
    args = config_cookies.build_args(browser="chrome", keyring="gnomekeyring")
    idx = args.index("--cookies-from-browser")
    assert args[idx + 1] == "chrome+gnomekeyring"

def test_container_uses_double_colon(self):
    args = config_cookies.build_args(browser="firefox", container="Work")
    idx = args.index("--cookies-from-browser")
    assert args[idx + 1] == "firefox::Work"

def test_profile_and_container_double_colon(self):
    args = config_cookies.build_args(browser="firefox", profile="default", container="Work")
    idx = args.index("--cookies-from-browser")
    assert args[idx + 1] == "firefox:default::Work"

def test_keyring_plus_profile(self):
    args = config_cookies.build_args(browser="chrome", keyring="gnomekeyring", profile="Default")
    idx = args.index("--cookies-from-browser")
    assert args[idx + 1] == "chrome+gnomekeyring:Default"

def test_all_fields(self):
    args = config_cookies.build_args(
        browser="firefox", keyring="gnomekeyring", profile="default", container="Work"
    )
    idx = args.index("--cookies-from-browser")
    assert args[idx + 1] == "firefox+gnomekeyring:default::Work"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
uv run pytest qa/yt-dlp/test_batch_config_commands.py::TestConfigCookies -v
```

Expected: New tests FAIL (wrong separator format).

- [ ] **Step 3: Fix the browser spec construction**

Read `skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/config_cookies.py`.
Replace the browser spec construction (lines 18-31) with:

```python
    # Build the browser spec: BROWSER[+KEYRING][:PROFILE][::CONTAINER]
    browser_spec = browser
    if keyring:
        browser_spec += f"+{keyring}"
    if profile:
        browser_spec += f":{profile}"
    if container:
        browser_spec += f"::{container}"
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
uv run pytest qa/yt-dlp/test_batch_config_commands.py::TestConfigCookies -v
```

Expected: ALL tests pass (old and new).

- [ ] **Step 5: Commit**

```bash
git add skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/config_cookies.py qa/yt-dlp/test_batch_config_commands.py
git commit -m "fix(yt-dlp): correct browser spec format — + for keyring, :: for container"
```

---

### Task 3: Fix authentication.md CRLF/LF claim (R1 — OBJECTIVE)

R1 says the yt-dlp FAQ states line endings DO matter. Our earlier fix changed
the page to say they don't. Need to verify and correct.

**Files:**
- Modify: `skill-repo/yt-dlp/references/techniques/authentication.md`

- [ ] **Step 1: Verify the claim against yt-dlp source**

Search the yt-dlp FAQ and source code for cookie line ending handling.
Use WebSearch or WebFetch to check https://github.com/yt-dlp/yt-dlp/wiki/FAQ
for any mention of line endings or CRLF.

- [ ] **Step 2: Fix the claim based on evidence**

Read `skill-repo/yt-dlp/references/techniques/authentication.md`. Find the
line about CRLF/LF (around line 86).

If the FAQ confirms line endings matter, change to:
```
- Use correct line endings for your OS (CRLF on Windows, LF on Unix) — incorrect formatting can trigger HTTP 400 errors
```

If the FAQ says nothing or is ambiguous, change to:
```
- Use correct line endings for your OS (CRLF on Windows, LF on Unix) to avoid potential HTTP 400 errors
```

- [ ] **Step 3: Commit**

```bash
git add skill-repo/yt-dlp/references/techniques/authentication.md
git commit -m "fix(yt-dlp): correct CRLF/LF cookie file guidance per yt-dlp FAQ"
```

---

### Task 4: Fix network-and-performance.md retry-sleep syntax (R1 — OBJECTIVE)

`--retry-sleep 5` without a type prefix is likely invalid. Should be
`--retry-sleep http:5`.

**Files:**
- Modify: `skill-repo/yt-dlp/references/techniques/network-and-performance.md`

- [ ] **Step 1: Verify the syntax**

Run: `yt-dlp --retry-sleep 5 --simulate "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>&1 | head -5`

If it errors, the type prefix is required. If it works, it defaults to http.

Note: yt-dlp may not be on PATH. Use the full path:
`"C:/Users/jeffr/AppData/Roaming/Python/Python313/Scripts/yt-dlp.exe"`

- [ ] **Step 2: Fix the example based on evidence**

Read `skill-repo/yt-dlp/references/techniques/network-and-performance.md`.
Find line 108 with `--retry-sleep 5`.

If the bare syntax is invalid, change to:
```bash
# Simple: sleep 5 seconds between HTTP retries
yt-dlp --retry-sleep http:5 "URL"
```

If it works but is ambiguous, add a note:
```bash
# Sleep 5 seconds between HTTP retries (type prefix recommended)
yt-dlp --retry-sleep http:5 "URL"
```

- [ ] **Step 3: Commit**

```bash
git add skill-repo/yt-dlp/references/techniques/network-and-performance.md
git commit -m "fix(yt-dlp): add type prefix to --retry-sleep example"
```

---

### Task 5: Document --force-overwrites default (R3 — OBJECTIVE)

Every download/process command adds `--force-overwrites` silently. This changes
yt-dlp's default behavior and should be documented.

**Files:**
- Modify: `skill-repo/yt-dlp/SKILL.md`
- Modify: `skill-repo/yt-dlp/references/gotchas.md`

- [ ] **Step 1: Add to SKILL.md**

Read `skill-repo/yt-dlp/SKILL.md`. After the Quick Examples section, add a
note:

```markdown
### Default Behavior

- **Force overwrites:** All commands include `--force-overwrites` by default to
  avoid interactive prompts in agent context. Pass `--no-overwrites` to prevent
  overwriting existing files.
```

- [ ] **Step 2: Add to gotchas.md**

Read `skill-repo/yt-dlp/references/gotchas.md`. Add under the "Agent-Specific
Issues" section:

```markdown
### Force overwrites by default
All CLI commands add `--force-overwrites` automatically to prevent yt-dlp from
hanging on interactive overwrite prompts. This means existing files WILL be
overwritten without warning. Use `--no-overwrites` to prevent this.
```

- [ ] **Step 3: Commit**

```bash
git add skill-repo/yt-dlp/SKILL.md skill-repo/yt-dlp/references/gotchas.md
git commit -m "docs(yt-dlp): document --force-overwrites default behavior"
```

---

### Task 6: Fix wiki-code alignment divergences (R3 — OBJECTIVE x4)

Four documentation mismatches between SKILL.md/wiki and the actual code.

**Files:**
- Modify: `skill-repo/yt-dlp/SKILL.md`
- Modify: `skill-repo/yt-dlp/references/techniques/audio-extraction.md`

- [ ] **Step 1: Fix SKILL.md playlist output template**

Read `skill-repo/yt-dlp/SKILL.md`. Find the playlist example (around line 68).
The example shows `%(playlist_title)s/%(title)s.%(ext)s` but the code defaults
to `%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s`.

Update the example to match the code:
```bash
uv run yt_dlp_cli.py download playlist "https://youtube.com/playlist?list=..." --output "%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s"
```

Or better — remove the `--output` flag from the example since the default
is already good, and add a note that the default organizes by playlist with
numbered files.

- [ ] **Step 2: Fix channel date format in code**

Read `skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/download_channel.py`.
Change the default output template (around line 39) from:
```python
args.extend(["-o", "%(channel)s/%(upload_date)s - %(title)s.%(ext)s"])
```
To:
```python
args.extend(["-o", "%(channel)s/%(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s"])
```

This matches the wiki recommendation (readable date + video ID for dedup).

- [ ] **Step 3: Update channel test for new default template**

Read `qa/yt-dlp/test_download_commands.py`. Update
`TestDownloadChannel::test_default_output_template_contains_channel`:

```python
def test_default_output_template_contains_channel(self):
    args = download_channel.build_args(self.URL)
    idx = args.index("-o")
    template = args[idx + 1]
    assert "channel" in template
    assert "upload_date" in template
    assert "id" in template
```

- [ ] **Step 4: Document audio quality named levels**

Read `skill-repo/yt-dlp/references/techniques/audio-extraction.md`. Add a
section or table documenting the CLI wrapper's named quality levels:

```markdown
### Quality Levels (CLI wrapper)

The CLI wrapper accepts named quality levels that map to yt-dlp's 0-10 scale:

| Name | yt-dlp value | Approximate bitrate (MP3) |
|------|-------------|--------------------------|
| best | 0 | ~256-320 kbps |
| high | 2 | ~192-256 kbps |
| medium (default) | 5 | ~128-192 kbps |
| low | 8 | ~64-96 kbps |
| worst | 10 | ~32-48 kbps |

You can also pass raw bitrate values: `--quality 192` or `--quality 192K`.
```

- [ ] **Step 5: Add sponsorblock no-op warning**

Read `skill-repo/yt-dlp/references/techniques/post-processing.md`. Add to the
gotchas section:

```markdown
- **`process sponsorblock` requires `--remove` or `--mark`.** Running the command
  without either flag downloads the video with no SponsorBlock action — a silent no-op.
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest qa/yt-dlp/ -v --tb=short
```

Expected: All pass (only the channel template test changed).

- [ ] **Step 7: Commit**

```bash
git add skill-repo/yt-dlp/SKILL.md skill-repo/yt-dlp/scripts/yt_dlp_cli/commands/download_channel.py qa/yt-dlp/test_download_commands.py skill-repo/yt-dlp/references/techniques/audio-extraction.md skill-repo/yt-dlp/references/techniques/post-processing.md
git commit -m "fix(yt-dlp): align wiki, SKILL.md, and code — templates, quality levels, sponsorblock warning"
```

---

### Task 7: Harden weak tests (R4 — OBJECTIVE)

Fix the systemic test weaknesses: performance flag adjacency checks,
presence-only tests, and untested parameters.

**Files:**
- Modify: `qa/yt-dlp/test_download_commands.py`
- Modify: `qa/yt-dlp/test_process_commands.py`
- Modify: `qa/yt-dlp/test_batch_config_commands.py`

- [ ] **Step 1: Fix performance flag tests to check adjacency**

In `test_download_commands.py`, `TestDownloadVideo::test_performance_flags`:

Change from:
```python
assert "-N" in args
assert "4" in args
assert "-r" in args
assert "50K" in args
```
To:
```python
idx_n = args.index("-N")
assert args[idx_n + 1] == "4"
idx_r = args.index("-r")
assert args[idx_r + 1] == "50K"
```

Apply the same pattern to:
- `test_batch_config_commands.py::TestBatchFromFile::test_performance_flags`
- `test_batch_config_commands.py::TestBatchFromFile::test_sleep_intervals`
- `test_batch_config_commands.py::TestBatchSync::test_sleep_intervals`
- `test_download_commands.py::TestDownloadPlaylist::test_sleep_intervals`
- `test_download_commands.py::TestDownloadPlaylist::test_date_filters` (check values)
- `test_download_commands.py::TestDownloadChannel::test_date_range` (check values)
- `test_download_commands.py::TestDownloadChannel::test_archive` (check value)

- [ ] **Step 2: Fix presence-only tests in process_commands.py**

In `test_process_commands.py`, for TestChapters and TestEmbed, change tests
like:
```python
assert "-o" in args
```
To:
```python
idx = args.index("-o")
assert args[idx + 1] == "%(title)s.%(ext)s"  # or whatever the test value is
```

Apply to all 6 presence-only tests flagged by R4:
- `TestChapters::test_output`
- `TestChapters::test_output_dir`
- `TestChapters::test_cookies`
- `TestEmbed::test_output`
- `TestEmbed::test_output_dir`
- `TestEmbed::test_cookies`

- [ ] **Step 3: Add missing parameter tests for download_channel**

In `test_download_commands.py`, add to `TestDownloadChannel`:

```python
def test_cookies(self):
    args = download_channel.build_args(self.URL, cookies="cookies.txt")
    idx = args.index("--cookies")
    assert args[idx + 1] == "cookies.txt"

def test_no_overwrites(self):
    args = download_channel.build_args(self.URL, no_overwrites=True)
    assert "--no-overwrites" in args
    assert "--force-overwrites" not in args

def test_max_downloads(self):
    args = download_channel.build_args(self.URL, max_downloads=10)
    idx = args.index("--max-downloads")
    assert args[idx + 1] == "10"

def test_sleep_intervals(self):
    args = download_channel.build_args(self.URL, sleep_interval=2.0, max_sleep_interval=5.0)
    idx_s = args.index("--sleep-interval")
    assert args[idx_s + 1] == "2.0"
    idx_m = args.index("--max-sleep-interval")
    assert args[idx_m + 1] == "5.0"

def test_concurrent_fragments(self):
    args = download_channel.build_args(self.URL, concurrent_fragments=4)
    idx = args.index("-N")
    assert args[idx + 1] == "4"

def test_rate_limit(self):
    args = download_channel.build_args(self.URL, rate_limit="1M")
    idx = args.index("-r")
    assert args[idx + 1] == "1M"
```

- [ ] **Step 4: Add missing parameter tests for download_playlist**

Similar additions for `TestDownloadPlaylist`: cookies, no_overwrites,
concurrent_fragments, rate_limit.

- [ ] **Step 5: Run all tests**

```bash
uv run pytest qa/yt-dlp/ -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add qa/yt-dlp/test_download_commands.py qa/yt-dlp/test_process_commands.py qa/yt-dlp/test_batch_config_commands.py
git commit -m "test(yt-dlp): harden weak tests — adjacency checks, value assertions, missing params"
```

---

### Task 8: Address judgment calls — wiki improvements

These are the non-blocking judgment calls. Address each one with a targeted fix.

**Files:**
- Modify: `skill-repo/yt-dlp/references/techniques/audio-extraction.md`
- Modify: `skill-repo/yt-dlp/references/techniques/post-processing.md`
- Modify: `skill-repo/yt-dlp/references/techniques/output-templates.md`
- Modify: `skill-repo/yt-dlp/references/techniques/format-selection.md`
- Modify: `skill-repo/yt-dlp/references/techniques/authentication.md`
- Modify: `skill-repo/yt-dlp/SKILL.md`

- [ ] **Step 1: audio-extraction.md — warn about subs in mp3**

Read the file. Find the "full music download" recipe (around line 98-100).
Add a warning:

```markdown
> Note: `--embed-subs` is silently ignored for audio-only containers (mp3, m4a, etc.)
> since subtitles cannot be embedded in audio files.
```

- [ ] **Step 2: post-processing.md — add Windows note to --exec**

Read the file. Find the `--exec` example (around line 204). Add:

```markdown
> Note: `--exec` commands are OS-specific. Use `mv` on Unix, `move` on Windows.
> Use `--exec "echo {}"` to test before running destructive commands.
```

- [ ] **Step 3: output-templates.md — warn about illegal filename chars**

Read the file. Add to the gotchas section:

```markdown
- **Video titles may contain illegal filename characters.** On Windows, characters
  like `<>:"/\|?*` in titles will cause download failures. Use `--restrict-filenames`
  (ASCII-safe) or `--windows-filenames` (removes Windows-illegal chars only) to prevent this.
```

- [ ] **Step 4: format-selection.md — fix ? operator example**

Read the file. Find line 113. Change `[filesize<?50M]` to `[filesize<=?50M]`
to be consistent with the documented operator syntax.

- [ ] **Step 5: authentication.md — source the 30-minute claim or soften it**

Read the file. Find line 207. Change:

```markdown
Refresh cookies within 30 minutes for Cloudflare sites
```
To:
```markdown
Refresh cookies frequently for Cloudflare-protected sites — challenge tokens
expire quickly (often within minutes to hours depending on the site)
```

- [ ] **Step 6: SKILL.md — add more trigger phrases and default output note**

Read SKILL.md. In the description frontmatter, add platform trigger phrases:
`download from Instagram`, `download from Vimeo`, `download from Twitch`,
`download Twitch clip`, `download Instagram reel`.

After the Quick Examples, add:

```markdown
### Defaults

- Files download to the current working directory unless `--output-dir` is specified
- Existing files are overwritten by default (use `--no-overwrites` to prevent)
```

- [ ] **Step 7: Commit**

```bash
git add skill-repo/yt-dlp/references/techniques/audio-extraction.md skill-repo/yt-dlp/references/techniques/post-processing.md skill-repo/yt-dlp/references/techniques/output-templates.md skill-repo/yt-dlp/references/techniques/format-selection.md skill-repo/yt-dlp/references/techniques/authentication.md skill-repo/yt-dlp/SKILL.md
git commit -m "docs(yt-dlp): address judgment calls from adversarial review"
```

---

### Task 9: Update log and run final verification

**Files:**
- Modify: `skill-repo/yt-dlp/references/log.md`

- [ ] **Step 1: Update the skill log**

Append to `skill-repo/yt-dlp/references/log.md`:

```markdown
## 2026-04-15: Adversarial review fixes

Full adversarial review found 15 objective failures and 14 judgment calls.
Fixed:
- CLI invocation (added yt_dlp_cli.py shim script)
- config_cookies browser spec bug (+ for keyring, :: for container)
- CRLF/LF cookie guidance corrected
- --retry-sleep syntax fixed with type prefix
- Documented --force-overwrites default
- Aligned SKILL.md/wiki with code (playlist template, channel date format,
  audio quality levels, sponsorblock no-op warning)
- Hardened 15+ weak tests (adjacency checks, value assertions, missing params)
- Wiki improvements: subs-in-mp3 warning, --exec Windows note, illegal
  filename chars, format-selection ? operator, Cloudflare cookie advice
```

- [ ] **Step 2: Run full static checks**

```bash
uv run qa/check_links.py yt-dlp
uv run pytest qa/yt-dlp/ -v
```

Expected: 0 broken links, 0 orphans, all tests pass.

- [ ] **Step 3: Commit**

```bash
git add skill-repo/yt-dlp/references/log.md
git commit -m "docs(yt-dlp): log adversarial review fixes"
```
