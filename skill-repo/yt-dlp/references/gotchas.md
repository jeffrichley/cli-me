# yt-dlp Gotchas

## Agent-Specific Issues

### No interactive prompts
yt-dlp may prompt for confirmation (e.g., overwrite existing files). In agent context,
always use `--force-overwrites` or `--no-overwrites` to avoid hanging.

### PATH issues on Windows
yt-dlp may not be on PATH when installed via pip. The backend module must search
common install locations:
- `C:/Users/<user>/AppData/Roaming/Python/Python3*/Scripts/yt-dlp.exe`
- `C:/Users/<user>/AppData/Local/Programs/Python/Python3*/Scripts/yt-dlp.exe`

### Force overwrites by default
All CLI commands add `--force-overwrites` automatically to prevent yt-dlp from
hanging on interactive overwrite prompts. This means existing files WILL be
overwritten without warning. Use `--no-overwrites` to prevent this.

### ffmpeg dependency
Many post-processing operations require ffmpeg. If ffmpeg is not installed,
yt-dlp will fail silently or produce incomplete output. Always check for
ffmpeg availability when using `-x`, `--embed-*`, `--remux-video`, etc.

### Cookie extraction requires browser to be closed
`--cookies-from-browser` may fail if the browser is currently running and has
locked its cookie database. Warn the user to close the browser first.

## Download-Specific Issues

### YouTube throttling
YouTube throttles direct downloads. yt-dlp handles this internally but
concurrent fragment downloads (`-N`) can help with speed.

### Geo-restricted content
Some content is geo-restricted. Use `--geo-bypass` or `--proxy` to work around.
Note: `--geo-bypass` uses a fake X-Forwarded-For header and doesn't always work.

### Age-restricted content
Requires authentication (cookies or credentials). `--cookies-from-browser`
is the easiest approach.

### Rate limiting
Sites may rate-limit aggressive downloads. Use `--sleep-interval` and
`--max-sleep-interval` for polite downloading. Essential for batch operations.
