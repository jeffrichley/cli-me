# Pandoc Slides Design

## Goal

Add first-class slide generation to the pandoc skill with a dedicated `slides`
command group. The first release supports only `beamer` and `revealjs`, using
one generic build command and a deliberately small set of slide-focused flags.

## Scope

In scope:

- new `slides` Typer group under the pandoc CLI
- one command: `slides build INPUT OUTPUT --to beamer|revealjs`
- support for the common slide flags:
  - `--from`
  - `--slide-level`
  - `--incremental`
  - `--standalone`
  - `--toc`
  - `--metadata`
  - `--variable`
  - `--pdf-engine`
  - `--embed-resources`
- validation for invalid writer/flag combinations
- command-graph and integration QA
- documentation updates across `SKILL.md`, the wiki, and the QA playbook

Out of scope:

- `slidy`, `s5`, `dzslides`, `slideous`
- dedicated theme, transition, notes, background-image, or multi-column flags
- speaker-note helpers
- reveal.js asset bootstrapping beyond what pandoc already provides
- slide-specific template helpers

## Command Surface

The new user-facing surface is:

```bash
uv run pandoc_cli.py slides build INPUT OUTPUT --to beamer|revealjs [options]
```

The `slides` group is a peer of the existing `convert`, `citations`,
`templates`, `filters`, and `info` groups. It exists because slides are a
distinct workflow family with writer-specific options and validation rules that
would make `convert to` noisier and less coherent if they were added there.

The first release uses a single `build` command instead of separate
`slides beamer` and `slides revealjs` commands. That keeps shared behavior in
one place while still making slide intent explicit through the required
`--to beamer|revealjs` flag.

## Architecture

The implementation follows the same split used elsewhere in the pandoc skill:

- `skill-repo/pandoc/scripts/pandoc_cli/slides.py`
  - thin Typer dispatch layer
  - owns argument declarations and help text
- `skill-repo/pandoc/scripts/pandoc_cli/commands/slides_build.py`
  - owns argv construction
  - owns writer-specific validation
  - calls the shared subprocess backend
- `skill-repo/pandoc/scripts/pandoc_cli/__init__.py`
  - registers the new `slides` group with the root app

The shared backend in `pandoc_cli/backend.py` remains the single place that
finds pandoc, checks PDF engines, runs subprocesses, and forwards pandoc
stderr. The slides command should reuse those helpers rather than adding new
process-management logic.

## Behavior

`slides build` forwards the following shared options directly to pandoc:

- `INPUT -o OUTPUT`
- `--from`
- `--to`
- `--slide-level`
- `--incremental`
- `--standalone` / `--standalone=false`
- `--toc`
- repeated `--metadata KEY=VALUE`
- repeated `--variable KEY=VALUE`

The wrapper should stay opinionated and minimal. It should not try to model
every slide-writer-specific pandoc feature in v1. Theme and layout tuning stay
available through repeated `--variable` options, which is consistent with how
the existing wrapper handles templates.

## Validation Rules

The command should enforce the following rules before invoking pandoc:

1. `INPUT` must exist.
2. `--to` is required and must be either `beamer` or `revealjs`.
3. `beamer` rejects `--embed-resources`.
4. `revealjs` rejects `--pdf-engine`.
5. If the effective output is a PDF path and the writer is `beamer`, reuse the
   existing PDF engine availability checks from the backend.
6. If `OUTPUT` is `-`, allow it only for reveal.js output. Do not allow stdout
   for beamer PDF-style output paths.

The goal is not to shield users from all pandoc errors. The wrapper validates
the combinations that are clearly incoherent at the slides-workflow level and
otherwise lets pandoc remain the source of truth.

## Output Semantics

For `beamer`:

- primary expected output is a PDF deck
- `--pdf-engine` is supported and validated using the existing backend helpers
- output verification in integration tests should assert PDF magic when a PDF
  is produced

For `revealjs`:

- primary expected output is an HTML deck
- `--embed-resources` is allowed
- integration tests should assert HTML slide markers rather than merely
  checking file existence

The command does not attempt to normalize non-standard output paths. If the
user provides an odd extension, pandoc remains responsible for interpreting it.
The wrapper only enforces the writer/flag compatibility rules above.

## Testing Strategy

The slides slice must follow the same two-tier QA model used by the rest of the
pandoc skill.

### Tier 1

Create `qa/pandoc/test_slides_commands.py` with tests for:

- exact argv construction for `beamer`
- exact argv construction for `revealjs`
- repeated `--metadata` forwarding
- repeated `--variable` forwarding
- `--slide-level` and `--incremental` forwarding
- rejection of `beamer + --embed-resources`
- rejection of `revealjs + --pdf-engine`
- required `--to`
- missing input file
- stdout restriction behavior

These tests should patch the command logic module and assert the exact pandoc
argv list, matching the established command-graph pattern.

### Tier 2

Create `qa/pandoc/test_slides_integration.py` with end-to-end tests for:

- reveal.js HTML generation against the real pandoc binary
- beamer PDF generation when a LaTeX engine is available
- clean skipping when LaTeX support is absent
- format-specific output assertions:
  - HTML deck contains reveal.js slide structure markers
  - PDF deck begins with `%PDF-`

As with the rest of the pandoc skill, “file exists and is non-empty” is not
sufficient.

## Documentation Changes

The following documentation updates are required:

- `skill-repo/pandoc/SKILL.md`
  - add `slides build`
  - remove or narrow the statement that slides are deferred
- `skill-repo/pandoc/references/index.md`
  - add a `Slides` technique page
  - update the deferred-features summary
- `skill-repo/pandoc/references/techniques/slides.md`
  - document the supported writers
  - show example commands for `beamer` and `revealjs`
  - explain that writer-specific customization is passed through `--variable`
- `skill-repo/pandoc/references/future-scope.md`
  - remove `beamer` and `revealjs` from the deferred list
  - leave the older slide writers and deeper slide features deferred
- `qa/pandoc/playbook.md`
  - add the full command contract for `slides build`

## Error Handling

The slides command should follow the current pandoc wrapper style:

- use `typer.echo(..., err=True)` for wrapper-level validation failures
- raise `typer.Exit(code=1)` for wrapper-level validation failures
- let `backend.run_pandoc()` surface pandoc's own stderr verbatim on subprocess
  failure

This preserves the current user experience: clear wrapper errors for wrapper
problems, and raw pandoc errors for pandoc problems.

## File Plan

Create:

- `skill-repo/pandoc/scripts/pandoc_cli/slides.py`
- `skill-repo/pandoc/scripts/pandoc_cli/commands/slides_build.py`
- `qa/pandoc/test_slides_commands.py`
- `qa/pandoc/test_slides_integration.py`
- `skill-repo/pandoc/references/techniques/slides.md`

Modify:

- `skill-repo/pandoc/scripts/pandoc_cli/__init__.py`
- `skill-repo/pandoc/SKILL.md`
- `skill-repo/pandoc/references/index.md`
- `skill-repo/pandoc/references/future-scope.md`
- `qa/pandoc/playbook.md`

## Success Criteria

The slides slice is complete when:

- `slides build` is registered and callable
- `beamer` and `revealjs` are intentionally supported
- invalid flag/writer combinations fail before pandoc is invoked
- command-graph and integration tests cover the new surface
- docs no longer describe `beamer` and `revealjs` slide generation as deferred
- older slide writers remain explicitly deferred

## Non-Goals

This slice does not try to become a full slide-authoring abstraction over
pandoc. It adds a clean, explicit, tested workflow entry point for the two
slide writers that matter now and leaves the deeper surface for later demand.
