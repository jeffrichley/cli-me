# Meta-Skill Learning Log

Append-only. Newest entries at the bottom.

---

**2026-04-15** — First skill built: ffmpeg. Initial lessons:

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

---

**2026-04-15** — Adversarial review system built and battle-tested (3 full rounds).

8. **Adversarial reviews find what build processes miss.** Round 1 found: a runtime crash
   bug (Twitter filter syntax), 78% dead URLs, 51% untested commands, systemic code-wiki
   divergence (128k vs 192k audio bitrate), and false-confidence tests. None of these were
   caught during the build process.

9. **Fresh context is non-negotiable.** Reviewer agents must have ZERO context from the
   creator's session. The same agent that built the code will rationalize its own mistakes.
   Different model is even better (creator: Sonnet, reviewer: Opus, or vice versa).

10. **Objective vs judgment split is critical.** Objective failures (wrong flags, dead URLs,
    crash bugs) get auto-fix loops with a 3-strike limit. Judgment calls (is this best
    practice actually best?) accumulate for human decision at phase boundaries. Without
    this split, the process either blocks forever or rubber-stamps everything.

11. **The 3-strike auto-fix loop works.** Reviewer finds issue → fix agent fixes → reviewer
    re-verifies. If the same issue persists after 3 cycles, escalate to human. This
    prevented infinite loops while ensuring issues got resolved.

12. **Code-wiki alignment is the highest-value review.** R3 (code-wiki alignment) found
    the most impactful issues: systemic audio bitrate divergence, missing pix_fmt, missing
    lanczos, missing profile/level flags. The pattern: agents write code that "works" but
    uses weaker settings than what the wiki documents. Always cross-reference.

13. **LLM reviewers spot-check. Deterministic tools check everything.** Three rounds of
    5 LLM reviewers (15 reviews total) caught ~5 dead URLs per round. A single run of
    `qa/check_urls.py` found all 37. For anything mechanically checkable (URLs, file
    existence, format validation), use a script. Reserve LLM reviewers for semantic
    issues (wrong commands, misleading explanations, edge cases).

14. **URL rot is constant and brutal.** The ffmpeg wiki went from 0% dead URLs at
    creation to 37 dead URLs within hours (the URLs were already dead when the research
    agents found them — the agents cited URLs they found in search results without
    verifying them). The deterministic URL checker must run at build time and periodically.

15. **The `-y` flag lesson.** ffmpeg hangs on interactive overwrite confirmation if `-y`
    is not passed. This was missed through the entire build process and two rounds of
    adversarial review — only caught in Round 3 by R2 (scaffold reviewer). Agent
    contexts don't have stdin, so any interactive prompt is a silent hang. Every CLI
    skill that wraps a tool with interactive prompts needs to suppress them.

16. **Conditional assertions are false-confidence traps.** The normalize test had its
    loudness assertion inside `if json_start >= 0` — if JSON parsing failed, the test
    silently passed with no loudness verification. Always assert that prerequisite
    conditions are met, don't make the real assertion conditional on them.

17. **"Runs" is not "works."** Running without errors proves syntax. Running with shallow
    assertions proves existence. Running with deep assertions proves correctness. Running
    with human review proves quality. Each level catches bugs the previous level misses.
    All four levels are needed.

---

**2026-04-15** — Process and architecture refinements.

18. **Thin wrappers + logic layer.** CLI commands should parse args and delegate to logic
    functions in a `commands/` module. Logic functions are independently testable without
    Typer. This separation makes Tier 1 tests cleaner (call the function directly instead
    of mocking subprocess through CliRunner) and enables reuse.

19. **Voice library doesn't belong in cli-me.** cli-me wraps existing tools. Custom data
    management (voice profiles, embeddings, LoRA storage) is orchestration, not tool
    wrapping. This belongs in a separate pipeline system.

20. **Skills that need API keys/config need a framework-level solution.** pyannote needs
    a HF token, ComfyUI needs a server URL, kohya_ss needs model paths. A central
    `~/.cli-me/config.toml` with global defaults and per-skill overrides is the right
    pattern. The `clime` CLI should have a `config` command.

21. **Research agents cite URLs without verifying them.** When agents search the web and
    write wiki pages, they include URLs from search results — but those URLs may already
    be dead (the search engine cached them). Always run the deterministic URL checker
    immediately after wiki pages are written, before any adversarial review.

22. **CLI tools are faster to build than GUI wrappers.** yt-dlp (already a CLI) was
    significantly faster to wrap than ffmpeg. The "thin wrapper + logic layer" pattern
    works identically — the skill adds agent-friendly structure and defaults on top of
    an already-rich CLI. No scripting API investigation needed.

23. **`--force-overwrites` is the yt-dlp equivalent of ffmpeg's `-y`.** Agent context
    has no stdin for interactive prompts. Every download command must include
    `--force-overwrites` or `--no-overwrites` explicitly. Same lesson as ffmpeg.

24. **Parallel agent implementation scales well for independent command groups.** Three
    agents implemented info, process, and batch+config groups simultaneously with no
    conflicts. The split-by-group architecture from lesson #3 enables this cleanly.

25. **URL checker reports example URLs as "dead".** Placeholder URLs like
    `https://www.youtube.com/playlist?list=PLAYLIST_ID` in code blocks are not broken
    source citations. The URL checker should eventually distinguish between URLs in
    `## Sources` sections vs. URLs in code blocks.

26. **Adversarial reviewers find more issues in research-generated content.** The R1
    reviewer found 8 factual errors in 10 technique pages — higher error rate than the
    ffmpeg build. Research agents are less precise than source-code analysis agents.
    The review pass is essential for research-heavy content.

27. **Decomposed adversarial-reviewers.md into individual files.** Split the
    monolithic file into protocol.md + 5 reviewer prompt files (r1–r5). Both
    cli-me-meta and the new adversarial-review skill read from the same files.
    Single source of truth for reviewer prompts.

28. **Created standalone adversarial-review skill.** `/adversarial-review <name>`
    runs static checks (link/orphan checker, URL checker, test suite) then
    dispatches all 5 reviewers in parallel. Report-only by default, --fix for
    auto-fix loop. Catches issues that build-time reviews miss because the
    skill has evolved since it was built.

29. **Link/orphan checker catches invisible files.** A markdown file that no
    other markdown file links to is invisible to LLM agents — they'll never
    discover it. The deterministic checker finds these instantly. Scoped to
    .md files only; Python orphans are caught by imports and test suites.

30. **index.md is a conventional entry point, like SKILL.md.** Agents find it
    because SKILL.md says "Start with references/index.md" in prose, not via
    a markdown link. Both are excluded from orphan detection as root nodes
    that sit above the link graph.

---

**2026-04-16** — Second skill built: demucs. New lessons:

31. **Installed version may differ from cloned source.** The demucs source repo
    had `--other-method`, `--clip-mode none`, `--list-models`, and `demucs.api`
    that didn't exist in the PyPI 4.0.1 release. Always run `binary --help` and
    compare against source analysis before wrapping. Unreleased features cause
    multiple rounds of rework when adversarial reviewers catch the mismatch.

32. **Timeout guidance is a prerequisite concern, not a nice-to-have.** ML tools
    (demucs, whisper, etc.) take minutes per invocation. Without explicit timeout
    guidance in SKILL.md, agents use default 2-minute Bash timeouts and kill
    processes mid-run. Add a "Default Behavior" section with timing estimates.

33. **`detect_device()` must use the same Python as the wrapped tool.** When the
    CLI runs in a uv venv but the tool is installed in system Python, `sys.executable`
    points to the wrong interpreter. Device detection (CUDA/MPS/CPU) must probe the
    tool's actual Python, not the wrapper's.

34. **R5 parallel subagent architecture.** Updated R5 to dispatch one subagent per
    technique page instead of running all commands sequentially. Benefit scales with
    command speed — marginal for demucs (5s/command) but significant for ffmpeg (ms).
