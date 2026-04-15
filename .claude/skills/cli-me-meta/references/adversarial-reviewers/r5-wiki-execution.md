## Reviewer 5: Wiki Execution Reviewer

**When:** After all commands are implemented (Phase 3d wiki verification)

**Dispatch as:** Fresh subagent with access to the real software binary

```
You are a verification agent. Your job is to run every CLI command documented
in the wiki technique pages and report whether each one actually works.

## What You're Verifying

Every command in the "CLI Commands" section of every technique page at:
skill-repo/<name>/references/techniques/*.md

## Process

For EACH technique page:

### 1. Read the page
Extract every command block from the "CLI Commands" section.

### 2. Generate test input
Use the synthetic fixture generators (ffmpeg -f lavfi for video/audio,
or other appropriate test data) to create the input each command needs.

### 3. Run each command
Execute the command exactly as documented. Capture:
- Exit code
- stdout
- stderr
- Output file(s) created

### 4. Verify output
- Does the output match what the page says to expect?
- Is the output format correct?
- Are the dimensions/duration/codec as documented?

### 5. Check all URLs
For EVERY URL in the Sources section:
- Fetch the URL
- Report: LIVE (200) / REDIRECT (3xx, note destination) / DEAD (4xx/5xx) /
  TIMEOUT / PAYWALL

### 6. Creative Hunt — Adversarial Inputs
After running the documented commands, try:
- Input with spaces in the filename
- Input with a very short duration (0.1 seconds)
- Input with no audio stream (for commands that expect audio)
- Input at an unusual resolution (e.g., 1x1, 99999x99999)
- Running the command twice on the same output (overwrite behavior)

## Report Format

For each technique page:

```
## [page-name.md]

### Command Results
| # | Command (abbreviated) | Exit Code | Output Valid | Notes |
|---|----------------------|-----------|-------------|-------|
| 1 | ffmpeg -i ... -c:v libx264 ... | 0 | YES | |
| 2 | ffmpeg -i ... -c copy ... | 0 | YES | |
| 3 | ... | 1 | NO | Error: "unrecognized option" |

### URL Status
| URL | Status |
|-----|--------|
| https://example.com/... | LIVE |
| https://example.com/old | DEAD (404) |

### Adversarial Input Results
| Input | Command | Result |
|-------|---------|--------|
| filename with spaces | convert format | PASS/FAIL |
| 0.1s video | extract clip | PASS/FAIL |

### Overall: ALL_PASS / PARTIAL_FAIL / MAJOR_FAIL
[summary of what needs fixing]
```
```

---

## Dispatch Notes

- **Never reuse a creator agent as a reviewer.** Fresh context only.
- **Reviewer agents should use a different model than the creator when possible.**
  If the creator used Sonnet, the reviewer uses Opus (or vice versa).
- **Reviewers report findings but do NOT fix issues.** The coordinator
  dispatches fixes based on findings.
- **A review that finds zero issues should be flagged as suspicious.**
  Either the work is genuinely perfect (rare) or the reviewer wasn't
  thorough enough. Consider re-dispatching with a more aggressive prompt.
- **URL verification requires WebFetch/WebSearch tools.** Ensure the
  reviewer agent has access to these.
