# Pandoc Deferred Backlog Roadmap

> **For agentic workers:** This is a decomposition-first roadmap, not an execution-ready single-spec implementation plan. Use it to pick one subsystem, run brainstorming for that subsystem only, then write a dedicated spec and detailed implementation plan before touching code.

**Goal:** Break the deferred pandoc backlog into implementable slices, define the recommended order, and identify the exact code, QA, and documentation surfaces each slice will modify.

**Architecture:** The current pandoc skill is a thin Typer CLI over a subprocess backend. New deferred work should preserve that shape: add a small command-group surface in `pandoc_cli/*.py`, keep argument construction and validation in `pandoc_cli/commands/*.py`, expand `references/` docs in parallel, and grow the QA suite with both Tier 1 command-graph tests and Tier 2 real-binary integration tests.

**Tech Stack:** Python 3.12, Typer, subprocess-driven pandoc invocation, pytest, CliRunner, pandoc 3.9.0.2 behavior as documented in the local source-analysis pages.

---

## Current Baseline

The existing pandoc skill already ships five stable command groups:

- `convert` in `skill-repo/pandoc/scripts/pandoc_cli/convert.py`
- `citations` in `skill-repo/pandoc/scripts/pandoc_cli/citations.py`
- `templates` in `skill-repo/pandoc/scripts/pandoc_cli/templates.py`
- `filters` in `skill-repo/pandoc/scripts/pandoc_cli/filters.py`
- `info` in `skill-repo/pandoc/scripts/pandoc_cli/info.py`

The command logic is intentionally split into:

- Typer surface in `skill-repo/pandoc/scripts/pandoc_cli/*.py`
- pure/imperfect command logic in `skill-repo/pandoc/scripts/pandoc_cli/commands/*.py`
- shared subprocess helpers in `skill-repo/pandoc/scripts/pandoc_cli/backend.py`
- documentation and backlog in `skill-repo/pandoc/references/*.md`
- QA coverage in `qa/pandoc/*.py`

The deferred backlog is authoritatively listed in:

- `skill-repo/pandoc/references/future-scope.md`
- `skill-repo/pandoc/SKILL.md`
- `skill-repo/pandoc/references/index.md`

## Sequencing Recommendation

Implement the deferred backlog in this order:

1. Slides
2. Jupyter notebooks
3. Math rendering, highlighting, and extension/introspection pass-through
4. Custom writers, advanced filter workflows, and deep template authoring
5. Exotic formats

This order is recommended because:

- slides and notebooks are the largest explicit product gaps already called out in `SKILL.md`
- the math/highlighting/extensions pass is smaller and mostly additive
- custom writers, advanced filters, and deep template authoring are higher-complexity expert workflows that benefit from experience gained in earlier slices
- exotic formats create broad test surface with the weakest current demand signal

## Phase 1: Slides

**Scope:** Add first-class slide generation support for beamer and reveal.js first, with later extension points for slidy, s5, dzslides, and slideous if demand appears.

**Recommended delivery split:**

1. `slides convert` for markdown to slide deck output
2. reveal.js-specific options
3. beamer-specific options
4. slide-oriented docs and gotchas

**Files to create:**

- `skill-repo/pandoc/scripts/pandoc_cli/slides.py`
- `skill-repo/pandoc/scripts/pandoc_cli/commands/slides_convert.py`
- `qa/pandoc/test_slides_commands.py`
- `qa/pandoc/test_slides_integration.py`
- `skill-repo/pandoc/references/techniques/slides.md`

**Files to modify:**

- `skill-repo/pandoc/scripts/pandoc_cli/__init__.py`
- `skill-repo/pandoc/SKILL.md`
- `skill-repo/pandoc/references/index.md`
- `skill-repo/pandoc/references/future-scope.md`
- `qa/pandoc/playbook.md`

**Core CLI decisions to settle during brainstorming:**

- whether slides get a dedicated `slides` command group or extend `convert to`
- whether MVP supports only `beamer` and `revealjs` or includes older HTML slide writers
- whether theme/transition options stay generic via repeatable `--variable` or become named flags
- whether speaker notes and background-image features are wrapped initially or deferred inside the slides slice

**Primary behavior to implement:**

- explicit writer targeting for `beamer` and `revealjs`
- slide-specific flags such as `--slide-level` and `--incremental`
- PDF engine validation for beamer outputs
- standalone/resource behavior for reveal.js outputs
- output validation rules for `.pdf` and `.html`

**QA additions:**

- Tier 1 tests for exact argv construction of slide-specific flags
- Tier 2 tests that generate a real beamer PDF when LaTeX is available
- Tier 2 tests that generate a real reveal.js HTML deck and assert slide markers
- error tests for invalid writer/flag combinations

**Success criteria:**

- users can intentionally request slide generation without using raw passthrough flags
- the skill docs explicitly say slides are now supported for the chosen writers
- `future-scope.md` is reduced to only the still-deferred slide features

## Phase 2: Jupyter Notebooks

**Scope:** Add first-class `ipynb` read/write support, with a deliberate policy for output preservation versus stripped roundtrips.

**Recommended delivery split:**

1. notebook conversion surface
2. notebook output policy
3. notebook docs and roundtrip QA

**Files to create:**

- `skill-repo/pandoc/scripts/pandoc_cli/notebooks.py`
- `skill-repo/pandoc/scripts/pandoc_cli/commands/notebooks_convert.py`
- `qa/pandoc/test_notebooks_commands.py`
- `qa/pandoc/test_notebooks_integration.py`
- `skill-repo/pandoc/references/techniques/notebooks.md`
- `qa/pandoc/fixtures/minimal.ipynb`

**Files to modify:**

- `skill-repo/pandoc/scripts/pandoc_cli/__init__.py`
- `skill-repo/pandoc/SKILL.md`
- `skill-repo/pandoc/references/index.md`
- `skill-repo/pandoc/references/future-scope.md`
- `skill-repo/pandoc/references/gotchas.md`
- `qa/pandoc/playbook.md`

**Core CLI decisions to settle during brainstorming:**

- whether notebooks get a dedicated `notebooks` group or a specialized `convert` subcommand
- whether the wrapper exposes `--ipynb-output` directly or via higher-level named options
- whether roundtrip support is limited to markdown to ipynb and ipynb to markdown for the first cut
- how much metadata preservation the wrapper promises versus documents as best-effort pandoc behavior

**Primary behavior to implement:**

- `ipynb` as an intentional, documented reader/writer target
- output-mode selection for notebook cell outputs
- clear validation and messaging around notebook-specific flags
- file-based roundtrip workflows with fixture-backed tests

**QA additions:**

- Tier 1 tests for notebook argv construction
- Tier 2 tests for markdown to ipynb generation
- Tier 2 tests for ipynb to markdown conversion
- Tier 2 tests around output-preservation policy using a small fixture notebook

**Success criteria:**

- notebook support is no longer called out as deferred in `SKILL.md`
- the chosen output policy is explicit in the docs and reflected in tests
- roundtrip expectations are documented to avoid accidental over-promising

## Phase 3: Math Rendering, Highlighting, and Extension Introspection

**Scope:** Add a smaller expert-user slice focused on exposing high-value existing pandoc flags without turning the wrapper into a raw-flag dump.

**Recommended delivery split:**

1. math-rendering options
2. highlighting options
3. extension/listing introspection

**Files to create:**

- `skill-repo/pandoc/scripts/pandoc_cli/commands/info_extensions.py`
- `skill-repo/pandoc/references/techniques/math-rendering.md`
- `skill-repo/pandoc/references/techniques/highlighting.md`
- `skill-repo/pandoc/references/techniques/extensions.md`
- `qa/pandoc/test_info_extensions_commands.py`
- `qa/pandoc/test_info_extensions_integration.py`

**Files to modify:**

- `skill-repo/pandoc/scripts/pandoc_cli/info.py`
- `skill-repo/pandoc/scripts/pandoc_cli/convert.py`
- `skill-repo/pandoc/scripts/pandoc_cli/commands/convert_to.py`
- `skill-repo/pandoc/SKILL.md`
- `skill-repo/pandoc/references/index.md`
- `skill-repo/pandoc/references/future-scope.md`
- `qa/pandoc/playbook.md`
- `qa/pandoc/test_convert_commands.py`
- `qa/pandoc/test_convert_integration.py`
- `qa/pandoc/test_info_commands.py`
- `qa/pandoc/test_info_integration.py`

**Core CLI decisions to settle during brainstorming:**

- whether math/highlighting flags belong on `convert to` or new subcommands
- whether to expose only a curated set of highlight and math flags or broader pass-through
- whether extension support should stop at `info extensions FORMAT` or include validation helpers

**Primary behavior to implement:**

- curated support for one HTML math mode path such as `--mathjax` and/or `--katex`
- curated support for highlight controls like `--highlight-style`, `--no-highlight`, `--syntax-definition`, and optionally `--listings`
- new introspection command for `pandoc --list-extensions=FORMAT`
- documentation tying extension syntax to existing `--from/--to` handling

**QA additions:**

- Tier 1 tests for argv construction and validation rules
- Tier 2 tests for HTML output containing the expected math/highlighting markers
- Tier 2 tests that verify extension listing returns known values for `markdown` or `gfm`

**Success criteria:**

- users get clear, documented access to the most valuable advanced rendering switches
- the wrapper stays opinionated and testable instead of exposing a generic raw-args escape hatch

## Phase 4: Custom Writers, Advanced Filters, and Deep Template Authoring

**Scope:** Add the high-skill expert workflows that require careful validation and documentation because the failure modes are subtle and easy to misuse.

**Recommended delivery split:**

1. custom Lua writers
2. advanced filter workflow helpers
3. deeper template authoring support

**Files to create:**

- `skill-repo/pandoc/scripts/pandoc_cli/writers.py`
- `skill-repo/pandoc/scripts/pandoc_cli/commands/writers_apply.py`
- `qa/pandoc/test_writers_commands.py`
- `qa/pandoc/test_writers_integration.py`
- `skill-repo/pandoc/references/techniques/custom-writers.md`
- `skill-repo/pandoc/references/techniques/advanced-filters.md`
- `skill-repo/pandoc/references/techniques/template-authoring.md`

**Files to modify:**

- `skill-repo/pandoc/scripts/pandoc_cli/__init__.py`
- `skill-repo/pandoc/scripts/pandoc_cli/filters.py`
- `skill-repo/pandoc/scripts/pandoc_cli/commands/filters_apply.py`
- `skill-repo/pandoc/scripts/pandoc_cli/templates.py`
- `skill-repo/pandoc/scripts/pandoc_cli/commands/templates_apply.py`
- `skill-repo/pandoc/SKILL.md`
- `skill-repo/pandoc/references/index.md`
- `skill-repo/pandoc/references/future-scope.md`
- `skill-repo/pandoc/references/gotchas.md`
- `qa/pandoc/playbook.md`

**Core CLI decisions to settle during brainstorming:**

- whether custom writers deserve a dedicated command group or remain an expert option on `convert`
- whether advanced filters are new commands or only documentation plus stricter validation
- whether deep template authoring includes new wrapper commands or only richer docs around existing `templates print/apply`

**Primary behavior to implement:**

- Lua writer path validation and friendly failure surfacing
- stronger filter-order and mixed-pipeline documentation surfaced in CLI help and docs
- optional helper commands around template introspection or default-template editing workflow

**QA additions:**

- Tier 1 tests for path validation and argv ordering
- Tier 2 tests for a tiny custom writer fixture if practical
- integration tests for filter-chain ordering with realistic examples

**Success criteria:**

- expert workflows become intentionally supported, not accidental side effects of generic pandoc behavior
- docs make the tradeoffs and footguns explicit

## Phase 5: Exotic Formats

**Scope:** Add targeted format-pair support only when a real use case appears.

**Recommended policy:**

- do not implement this phase as one large feature
- treat each requested family as its own micro-slice
- prefer documentation and validation before adding command-surface complexity

**Likely file touch points per requested format family:**

- `skill-repo/pandoc/scripts/pandoc_cli/convert.py`
- `skill-repo/pandoc/scripts/pandoc_cli/commands/convert_to.py`
- `skill-repo/pandoc/SKILL.md`
- `skill-repo/pandoc/references/index.md`
- `skill-repo/pandoc/references/future-scope.md`
- `skill-repo/pandoc/references/gotchas.md`
- `qa/pandoc/test_convert_commands.py`
- `qa/pandoc/test_convert_integration.py`

**Success criteria:**

- only requested formats are promoted from backlog
- each new format has format-specific integration assertions rather than generic “file exists” tests

## Cross-Cutting Rules For Every Phase

- preserve the current Typer split: user-facing CLI in `pandoc_cli/*.py`, testable logic in `pandoc_cli/commands/*.py`
- prefer additive command groups when a workflow is conceptually distinct
- avoid a generic `--raw-args` escape hatch
- update `SKILL.md`, `references/index.md`, `references/future-scope.md`, and `qa/pandoc/playbook.md` whenever a deferred area becomes supported
- add both Tier 1 and Tier 2 coverage for every new supported slice
- document platform-specific gotchas in `skill-repo/pandoc/references/gotchas.md`

## Definition of Done Per Slice

Do not mark a slice complete until all of the following are true:

- the command surface exists and is wired in `pandoc_cli/__init__.py`
- the new behavior is documented in `SKILL.md`
- the wiki has at least one new technique page and any new gotchas
- the playbook documents the new command contract
- Tier 1 tests cover argv construction and validation
- Tier 2 tests cover real pandoc behavior with format-specific assertions
- `future-scope.md` is edited so it reflects the remaining backlog accurately

## Suggested Brainstorm Sequence

Use this roadmap to drive the next conversations:

1. brainstorm `slides` only
2. write a dedicated slides spec
3. write a dedicated slides implementation plan
4. implement and verify slides
5. repeat the cycle for `notebooks`
6. repeat the cycle for `math/highlighting/extensions`
7. revisit later phases only after a demand signal or a concrete use case

## Risks

- overloading `convert to` until it becomes an incoherent expert-only interface
- promising notebook roundtrips more strongly than pandoc actually guarantees
- adding slide support without clearly separating reveal.js and beamer behavior
- broadening supported formats faster than the QA suite can make trustworthy
- turning documentation-heavy expert features into under-tested wrapper surface

## Recommended Immediate Next Step

Take this roadmap as the ordering and decomposition decision. The first detailed brainstorm should be the `slides` slice only.
