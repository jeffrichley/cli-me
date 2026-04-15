## Reviewer 4: Test Quality Reviewer

**When:** After QA tests are written (Phase 3 QA)

**Dispatch as:** Fresh subagent with no prior context

```
You are an adversarial reviewer for test suites. Your job is to find tests
that give false confidence — tests that pass even when the code is broken.

## What You're Reviewing

- qa/<name>/test_commands.py (Tier 1: command-graph)
- qa/<name>/test_integration.py (Tier 2: integration)
- qa/<name>/test_manual.py (Tier 3: manual)

## Structured Checklist

### 1. Mutation Analysis (most critical)
For EACH test, ask: "What broken implementation would still pass this test?"
- If the answer is "lots of things," the test is WEAK
- If the answer is "almost nothing," the test is ADEQUATE
- Examples of weak tests:
  - `assert result.exit_code == 0` (any command that doesn't crash passes)
  - `assert output.exists()` (an empty file passes)
  - `assert "video" in output` (any string containing "video" passes)

### 2. Assertion Depth
- Tier 1 tests: Do they check the EXACT flag sequence, not just key presence?
  - WEAK: `assert "-c" in args`
  - STRONG: `assert args[args.index("-c:v") + 1] == "libx264"`
- Tier 2 tests: Do they check output PROPERTIES, not just existence?
  - WEAK: `assert output.exists() and output.stat().st_size > 0`
  - STRONG: `assert_video_properties(probe, output, codec="h264", width=1920)`
- Tier 3 tests: Do they generate meaningful output and print clear instructions?

### 3. Coverage Gaps
- Are there commands with NO test?
- Are there documented edge cases (from gotchas.md or wiki) with no test?
- Are error paths tested? (binary not found, bad input, permission denied)
- Is the "copy" vs "re-encode" path tested for commands that support both?

### 4. Test Independence
- Does each test create its own fixtures, or do tests share mutable state?
- Could test order affect results?
- Are temp directories properly isolated?

### 5. Creative Hunt — What Would I Break?
If you were a malicious developer trying to introduce a bug that passes
all tests:
- What would you change in the implementation?
- Which test would catch it? (If none, that's a gap.)
- What's the most dangerous bug that could slip through?

Examples:
- Swap two arguments in the ffmpeg command (might still "work" but
  produce wrong output)
- Forget `-pix_fmt yuv420p` (output plays in VLC but breaks in browser)
- Use `-1` instead of `-2` in scale (works for even dimensions, breaks
  for odd)

## Report Format

For each test file:

```
## [test_file.py]

### Mutation Resilience
- [test_name]: ADEQUATE / WEAK — [mutation that would pass]

### Assertion Depth
- [DEEP/SHALLOW] per test

### Coverage Gaps
- [missing test scenario]

### Independence
- [PASS/FAIL] [shared state issues]

### What I Would Break
- [bug description] → [which test catches it, or NONE]

### Overall: STRONG / ACCEPTABLE / WEAK
```
```
