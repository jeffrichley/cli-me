# Meta-Skill Learning Log

Append-only. Newest entries at the bottom.

---

**2026-04-15** — First skill built: ffmpeg. Lessons learned:

1. **QA must come before implementation, not after.** We shipped 34 commands before
   testing any of them against real ffmpeg. Got lucky — all worked. Won't always be
   the case. Process now requires: write QA playbook → write Tier 1 tests → implement
   command → run Tier 1 → write Tier 2 → run Tier 2 → commit. Per command group.

2. **"File exists" is never a sufficient assertion.** First Tier 2 tests only checked
   if output existed and was nonzero. Had to push back twice to get real assertions:
   exact dimensions, pixel formats, magic bytes, duration precision, file size
   comparison, stream presence/absence, codec profiles, sample rates.

3. **Split CLI into modules from the start.** ffmpeg_cli.py became a 1000+ line single
   file with 34 commands. Should have been a package with one file per command group.
   Updated the typer-cli-template to enforce this for future skills.

4. **Parallel agent research is the killer feature.** 10 agents produced 35 deeply
   researched technique pages in ~5 minutes wall time. Quality was high — real commands,
   source URLs, common mistakes documented. This is the approach for every future skill.

5. **Wiki commands should be verified by running them.** The technique pages were written
   from web research but the exact commands were never tested. Added a verification step
   to Phase 3 of the meta-skill.

6. **Three-tier QA framework works well:**
   - Tier 1 (command-graph): mocks subprocess, verifies flag construction. Fast, no binary.
   - Tier 2 (integration): real binary, deep property assertions. The real quality gate.
   - Tier 3 (manual): generates files for human review. Catches what code can't assert.
   QA lives in qa/<name>/ — never shipped with the skill.

7. **Human-in-the-loop catches process gaps.** User caught: use hatchling not setuptools,
   use Rich for output, avoid brittle string tests, QA gap, "runs vs works" distinction.
   Each intervention improved the process permanently via meta-skill updates.
