---
title: Synthetic Fixture Trap
tags: [process, testing]
sources: [daily/2026-04-18.md]
created: 2026-04-18
updated: 2026-04-18
---

# Synthetic Fixture Trap

Synthetic test fixtures — sine tones, blank images, solid-color frames — can produce legitimately empty results from the tool under test, making assertions pass vacuously. The test runs, the assertion checks an empty collection, and the suite reports green. No actual behavior was verified.

## The Pyannote Case

The pyannote skill's integration tests used generated sine tone WAV files as input. Speaker diarization and voice activity detection correctly returned zero segments for a pure sine tone (no speech present). Assertion loops like `for segment in result: assert segment.duration > 0` iterated zero times — the test passed without asserting anything.

This is distinct from the [[concepts/assertion-depth|"file exists" anti-pattern]]: the assertions themselves were deep and correct. The problem was that the input data guaranteed they would never execute.

## The Pattern

The trap appears whenever:

1. The test fixture is synthetically generated (fast, reproducible, no licensing issues)
2. The tool legitimately produces empty or trivial output for that input
3. Assertions iterate over results rather than asserting result count first

## The Fix

Two complementary approaches:

- **Assert result count first.** Before iterating over results, assert that the collection is non-empty. This turns a vacuous pass into an explicit failure.
- **Use real-domain fixtures.** For speech tools, use actual speech samples. For image tools, use actual photographs. The fixture must exercise the tool's core detection/processing path.

Real-domain fixtures introduce complexity (licensing, file size, download requirements), but without them the test suite provides false confidence. A conditional integration test that skips when fixtures are unavailable is more honest than a synthetic test that always passes vacuously.

## Relationship to Assertion Depth

This is a fifth failure mode beyond the four levels described in [[concepts/assertion-depth]]: the assertions can be at Level 3 (deep, correct) but still verify nothing because the input was chosen poorly. Assertion depth measures the quality of the check; fixture quality measures whether the check gets exercised.

See also: [[concepts/assertion-depth]], [[concepts/qa-before-implementation]].
