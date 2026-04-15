# Gotchas

Cross-cutting issues and workarounds discovered through research and usage.

## pix_fmt yuv420p
Always include `-pix_fmt yuv420p` when encoding H.264 for web delivery. Without it,
ffmpeg may output yuv444p or yuv422p which breaks in browsers, QuickTime, and iOS.

## -ss placement
`-ss` before `-i` = fast (seeks to nearest keyframe). `-ss` after `-i` = accurate
(decodes from start). For most work, put it before `-i` and re-encode for frame accuracy.

## Windows paths
Windows backslashes and colons need escaping in filter strings. Use forward slashes
or escape: `subtitles='C\\:/path/to/file.srt'`

## -nostdin for batch
When running ffmpeg in a shell loop, add `-nostdin` before `-i` to prevent ffmpeg
from consuming stdin and killing the loop.

## Stream copy limitations
`-c copy` cannot be used with any filter (`-vf`, `-af`, `-filter_complex`).
It also cannot cut at arbitrary frames — only at keyframes.

## ffmpeg.org wiki blocked
As of April 2026, trac.ffmpeg.org returns Anubis anti-bot errors for automated access.
Use community resources (OTTVerse, Mux articles, Stack Overflow) for reference.
