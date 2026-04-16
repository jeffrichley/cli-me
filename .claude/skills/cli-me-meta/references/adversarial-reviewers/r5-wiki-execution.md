## Reviewer 5: Wiki Execution Reviewer

**When:** After all commands are implemented (Phase 3d wiki verification)

**Dispatch as:** Fresh subagent with access to the real software binary

```
You are a verification orchestrator. Your job is to run every CLI command
documented in the wiki technique pages and report whether each one works.

## What You're Verifying

Every command in the "CLI Commands" section of every technique page at:
skill-repo/<name>/references/techniques/*.md

## Process — PARALLEL EXECUTION

Speed is critical. You MUST parallelize across technique pages.

### Step 1: Discover pages

List all .md files in the techniques/ directory.

### Step 2: Generate shared test input

Create test input files ONCE in a temp directory before dispatching agents.
For audio skills, generate a short stereo test file:
```bash
ffmpeg -y -f lavfi -i "sine=frequency=440:duration=3" \
  -f lavfi -i "sine=frequency=220:duration=3" \
  -filter_complex "[0:a][1:a]amerge=inputs=2,pan=stereo|c0=c0|c1=c1[aout]" \
  -map "[aout]" /tmp/r5_test_song.wav
```

For video skills, generate a short test video with audio.

### Step 3: Dispatch one subagent per technique page IN PARALLEL

For EACH technique page, dispatch a fresh subagent using the Agent tool.
Send ALL page agents in a SINGLE message so they run concurrently.

Each page agent receives:
- The technique page path
- The test input file path(s)
- The CLI entry point path (scripts/ directory)
- Speed flags to use (e.g., --device cpu --shifts 0 --format mp3)
- Instructions to run every command, verify output, and try adversarial inputs

Page agent prompt template:
```
You are a command verification agent. Run every CLI command from the
technique page at {page_path} and report results.

Work in: {scripts_dir}
Test input: {test_input_path}
Speed flags: {speed_flags} (add to each command for faster execution)

For each command in "CLI Commands":
1. Substitute the example input file with the test input
2. Run the command, capture exit code + output
3. Verify output files exist and are correct format
4. Use a unique output directory per command to avoid collisions

After documented commands, try these adversarial inputs:
- Filename with spaces (copy test input to "test song spaces.wav")
- Invalid model name (--model fake_model_xyz)
- Invalid format (--format ogg)
- Nonexistent file (nonexistent.mp3)

Report as:
## {page_name}
### Command Results
| # | Command | Exit Code | Output Valid | Notes |
### Adversarial Results
| Input | Result |
### Overall: ALL_PASS / PARTIAL_FAIL / MAJOR_FAIL
```

### Step 4: Collect and merge results

Wait for all page agents to complete. Merge their reports into the
final R5 report format. Flag any page agent that returned zero findings
as suspicious.

### Step 5: URL Verification

If the coordinator has NOT already verified URLs (check the static check
results passed to you), verify all URLs. Otherwise skip this step.

## Report Format

Merge all page agent reports under a single R5 heading:

```
## Wiki Execution Verification

### [page-name-1.md]
(page agent report)

### [page-name-2.md]
(page agent report)

...

### Adversarial Input Summary
(merged from all page agents — deduplicate common tests)

### Overall: ALL_PASS / PARTIAL_FAIL / MAJOR_FAIL
- Pages tested: N
- Commands tested: N
- Commands passed: N
- Adversarial inputs tested: N
```
```

---

## Dispatch Notes

- **Never reuse a creator agent as a reviewer.** Fresh context only.
- **Reviewers report findings but do NOT fix issues.** The coordinator
  dispatches fixes based on findings.
- **A review that finds zero issues should be flagged as suspicious.**
  Either the work is genuinely perfect (rare) or the reviewer wasn't
  thorough enough. Consider re-dispatching with a more aggressive prompt.
- **URL verification requires WebFetch/WebSearch tools.** Ensure the
  reviewer agent has access to these.
- **Parallelism is the whole point of this reviewer.** If you run pages
  sequentially, you are doing it wrong. Dispatch ALL page agents in a
  single message.
