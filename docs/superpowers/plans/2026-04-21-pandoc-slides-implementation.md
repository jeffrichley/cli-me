# Pandoc Slides Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class `slides build` workflow to the pandoc skill for `beamer` and `revealjs`.

**Architecture:** Follow the existing pandoc wrapper split: add a thin Typer group in `pandoc_cli/slides.py`, keep argv construction and validation in `pandoc_cli/commands/slides_build.py`, reuse the shared subprocess backend, and add both Tier 1 command-graph tests and Tier 2 integration tests. Keep the CLI opinionated: shared slide flags only, with writer-specific tuning passed through repeated `--variable` options.

**Tech Stack:** Python 3.12, Typer, subprocess-driven pandoc invocation, pytest, CliRunner, local pandoc QA fixtures/helpers.

---

## File Structure

### New files

- `skill-repo/pandoc/scripts/pandoc_cli/slides.py`
  - Thin Typer command surface for `slides build`.
- `skill-repo/pandoc/scripts/pandoc_cli/commands/slides_build.py`
  - Pure argv builder and wrapper-level validation for slide workflows.
- `qa/pandoc/test_slides_commands.py`
  - Tier 1 command-graph tests for argv construction and validation.
- `qa/pandoc/test_slides_integration.py`
  - Tier 2 integration tests for reveal.js HTML and beamer PDF flows.
- `skill-repo/pandoc/references/techniques/slides.md`
  - Technique page documenting supported slide workflows and examples.

### Modified files

- `skill-repo/pandoc/scripts/pandoc_cli/__init__.py`
  - Register the new `slides` group.
- `skill-repo/pandoc/SKILL.md`
  - Advertise `slides build` and narrow the deferred slide scope.
- `skill-repo/pandoc/references/index.md`
  - Add the Slides technique page and update deferred summary.
- `skill-repo/pandoc/references/future-scope.md`
  - Remove `beamer` and `revealjs` from deferred slide scope.
- `qa/pandoc/playbook.md`
  - Add the full contract for `slides build`.

## Task 1: Add The `slides` CLI Group

**Files:**
- Create: `skill-repo/pandoc/scripts/pandoc_cli/slides.py`
- Modify: `skill-repo/pandoc/scripts/pandoc_cli/__init__.py`
- Test: `qa/pandoc/test_slides_commands.py`

- [ ] **Step 1: Write the failing CLI registration test**

```python
from typer.testing import CliRunner


def test_slides_group_is_registered():
    from pandoc_cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["slides", "--help"])

    assert result.exit_code == 0, result.output
    text = (result.stdout or result.output).lower()
    assert "build" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest qa/pandoc/test_slides_commands.py::test_slides_group_is_registered -v`
Expected: FAIL with `No such command 'slides'` or import failure because `slides.py` does not exist yet.

- [ ] **Step 3: Add the new Typer group to the pandoc root app**

Create `skill-repo/pandoc/scripts/pandoc_cli/slides.py`:

```python
"""slides command group — thin CLI dispatch for pandoc slide decks."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pandoc_cli import slides_app
from pandoc_cli.commands.slides_build import run_build


@slides_app.command("build")
def cmd_build(
    input: Path = typer.Argument(..., help="Input markdown file"),
    output: str = typer.Argument(..., help="Output file ('-' allowed for revealjs only)"),
    to: str = typer.Option(
        ...,
        "--to",
        help="Slide writer: beamer or revealjs",
    ),
    from_: Optional[str] = typer.Option(
        None,
        "--from",
        "-f",
        help="Override input format (e.g. markdown+yaml_metadata_block)",
    ),
    slide_level: Optional[int] = typer.Option(
        None,
        "--slide-level",
        help="Heading level that starts a new slide",
    ),
    incremental: bool = typer.Option(
        False,
        "--incremental",
        "-i",
        help="Make lists display incrementally",
    ),
    standalone: Optional[bool] = typer.Option(
        None,
        "--standalone/--no-standalone",
        help="Force standalone slide output or fragment-only output",
    ),
    toc: bool = typer.Option(False, "--toc", help="Insert a table of contents"),
    metadata: list[str] = typer.Option(
        [],
        "--metadata",
        "-M",
        help="Set document metadata as KEY=VALUE (repeatable)",
    ),
    variable: list[str] = typer.Option(
        [],
        "--variable",
        "-V",
        help="Set writer/template variable as KEY=VALUE (repeatable)",
    ),
    pdf_engine: Optional[str] = typer.Option(
        None,
        "--pdf-engine",
        help="PDF engine for beamer PDF output",
    ),
    embed_resources: bool = typer.Option(
        False,
        "--embed-resources",
        help="Inline linked assets for revealjs HTML output",
    ),
) -> None:
    """Build a slide deck using the beamer or revealjs writer."""
    run_build(
        str(input),
        output,
        to=to,
        from_=from_,
        slide_level=slide_level,
        incremental=incremental,
        standalone=standalone,
        toc=toc,
        metadata=list(metadata),
        variable=list(variable),
        pdf_engine=pdf_engine,
        embed_resources=embed_resources,
    )
```

Modify `skill-repo/pandoc/scripts/pandoc_cli/__init__.py`:

```python
"""pandoc CLI — universal document conversion."""

import typer

app = typer.Typer(
    name="pandoc-cli",
    help="Agent-native CLI for pandoc — convert, citations, templates, filters, info.",
    no_args_is_help=True,
)

convert_app = typer.Typer(help="Convert between formats (md, pdf, docx, html, epub, latex)", no_args_is_help=True)
citations_app = typer.Typer(help="Render citations from BibTeX / CSL bibliographies", no_args_is_help=True)
templates_app = typer.Typer(help="Apply custom templates and bundled Eisvogel preset", no_args_is_help=True)
filters_app = typer.Typer(help="Apply Lua / JSON filters; pandoc-crossref helpers", no_args_is_help=True)
info_app = typer.Typer(help="Introspection: version, formats, PDF engines available", no_args_is_help=True)
slides_app = typer.Typer(help="Build slide decks with beamer or revealjs", no_args_is_help=True)

app.add_typer(convert_app, name="convert")
app.add_typer(citations_app, name="citations")
app.add_typer(templates_app, name="templates")
app.add_typer(filters_app, name="filters")
app.add_typer(info_app, name="info")
app.add_typer(slides_app, name="slides")

import pandoc_cli.convert  # noqa: E402, F401
import pandoc_cli.citations  # noqa: E402, F401
import pandoc_cli.templates  # noqa: E402, F401
import pandoc_cli.filters  # noqa: E402, F401
import pandoc_cli.info  # noqa: E402, F401
import pandoc_cli.slides  # noqa: E402, F401
```

- [ ] **Step 4: Run the registration test to verify it passes**

Run: `pytest qa/pandoc/test_slides_commands.py::test_slides_group_is_registered -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skill-repo/pandoc/scripts/pandoc_cli/__init__.py skill-repo/pandoc/scripts/pandoc_cli/slides.py qa/pandoc/test_slides_commands.py
git commit -m "feat: add pandoc slides command group"
```

## Task 2: Implement Slide Arg Construction

**Files:**
- Create: `skill-repo/pandoc/scripts/pandoc_cli/commands/slides_build.py`
- Test: `qa/pandoc/test_slides_commands.py`

- [ ] **Step 1: Write failing argv-construction tests**

Add to `qa/pandoc/test_slides_commands.py`:

```python
import pytest


@pytest.mark.command_graph
def test_build_args_revealjs_happy_path():
    from pandoc_cli.commands.slides_build import build_args

    assert build_args(
        "deck.md",
        "deck.html",
        to="revealjs",
        from_="markdown",
        slide_level=2,
        incremental=True,
        standalone=True,
        toc=True,
        metadata=["title=Deck"],
        variable=["theme=black"],
        embed_resources=True,
    ) == [
        "deck.md",
        "-o",
        "deck.html",
        "--to",
        "revealjs",
        "--from",
        "markdown",
        "--slide-level",
        "2",
        "--incremental",
        "--standalone",
        "--toc",
        "--metadata",
        "title=Deck",
        "--variable",
        "theme=black",
        "--embed-resources",
    ]


@pytest.mark.command_graph
def test_build_args_beamer_happy_path():
    from pandoc_cli.commands.slides_build import build_args

    assert build_args(
        "deck.md",
        "deck.pdf",
        to="beamer",
        pdf_engine="xelatex",
        variable=["theme:default"],
    ) == [
        "deck.md",
        "-o",
        "deck.pdf",
        "--to",
        "beamer",
        "--pdf-engine",
        "xelatex",
        "--variable",
        "theme:default",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest qa/pandoc/test_slides_commands.py -k "build_args" -v`
Expected: FAIL with `ModuleNotFoundError` for `pandoc_cli.commands.slides_build`.

- [ ] **Step 3: Implement the pure argv builder**

Create `skill-repo/pandoc/scripts/pandoc_cli/commands/slides_build.py`:

```python
"""Logic for `slides build` — build a pandoc invocation and run it."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pandoc_cli.backend import find_pdf_engines, report_success, run_pandoc

_SLIDE_WRITERS = frozenset({"beamer", "revealjs"})


def build_args(
    input: str,
    output: str,
    *,
    to: str,
    from_: Optional[str] = None,
    slide_level: Optional[int] = None,
    incremental: bool = False,
    standalone: Optional[bool] = None,
    toc: bool = False,
    metadata: Optional[list[str]] = None,
    variable: Optional[list[str]] = None,
    pdf_engine: Optional[str] = None,
    embed_resources: bool = False,
) -> list[str]:
    args: list[str] = [str(input), "-o", str(output), "--to", to]

    if from_ is not None:
        args.extend(["--from", from_])
    if slide_level is not None:
        args.extend(["--slide-level", str(slide_level)])
    if incremental:
        args.append("--incremental")
    if standalone is True:
        args.append("--standalone")
    elif standalone is False:
        args.append("--standalone=false")
    if toc:
        args.append("--toc")
    for entry in metadata or []:
        args.extend(["--metadata", entry])
    for entry in variable or []:
        args.extend(["--variable", entry])
    if pdf_engine is not None:
        args.extend(["--pdf-engine", pdf_engine])
    if embed_resources:
        args.append("--embed-resources")

    return args
```

- [ ] **Step 4: Run the argv tests to verify they pass**

Run: `pytest qa/pandoc/test_slides_commands.py -k "build_args" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skill-repo/pandoc/scripts/pandoc_cli/commands/slides_build.py qa/pandoc/test_slides_commands.py
git commit -m "feat: add pandoc slides arg builder"
```

## Task 3: Implement Wrapper-Level Validation And Execution

**Files:**
- Modify: `skill-repo/pandoc/scripts/pandoc_cli/commands/slides_build.py`
- Test: `qa/pandoc/test_slides_commands.py`

- [ ] **Step 1: Write failing validation tests**

Add to `qa/pandoc/test_slides_commands.py`:

```python
from pathlib import Path
from unittest.mock import patch

import pytest
import typer


@pytest.mark.command_graph
def test_run_build_rejects_unknown_writer(tmp_path):
    from pandoc_cli.commands import slides_build

    src = tmp_path / "deck.md"
    src.write_text("# Deck\n", encoding="utf-8")

    with patch.object(slides_build, "run_pandoc") as mock_run:
        with pytest.raises(typer.Exit) as exc:
            slides_build.run_build(str(src), "deck.html", to="slidy")
    assert exc.value.exit_code == 1
    mock_run.assert_not_called()


@pytest.mark.command_graph
def test_run_build_rejects_beamer_embed_resources(tmp_path):
    from pandoc_cli.commands import slides_build

    src = tmp_path / "deck.md"
    src.write_text("# Deck\n", encoding="utf-8")

    with patch.object(slides_build, "run_pandoc") as mock_run:
        with pytest.raises(typer.Exit):
            slides_build.run_build(str(src), "deck.pdf", to="beamer", embed_resources=True)
    mock_run.assert_not_called()


@pytest.mark.command_graph
def test_run_build_rejects_revealjs_pdf_engine(tmp_path):
    from pandoc_cli.commands import slides_build

    src = tmp_path / "deck.md"
    src.write_text("# Deck\n", encoding="utf-8")

    with patch.object(slides_build, "run_pandoc") as mock_run:
        with pytest.raises(typer.Exit):
            slides_build.run_build(str(src), "deck.html", to="revealjs", pdf_engine="xelatex")
    mock_run.assert_not_called()


@pytest.mark.command_graph
def test_run_build_allows_revealjs_stdout(tmp_path):
    from pandoc_cli.commands import slides_build

    src = tmp_path / "deck.md"
    src.write_text("# Deck\n", encoding="utf-8")

    with patch.object(slides_build, "run_pandoc") as mock_run:
        slides_build.run_build(str(src), "-", to="revealjs")
    mock_run.assert_called_once()


@pytest.mark.command_graph
def test_run_build_rejects_beamer_stdout(tmp_path):
    from pandoc_cli.commands import slides_build

    src = tmp_path / "deck.md"
    src.write_text("# Deck\n", encoding="utf-8")

    with patch.object(slides_build, "run_pandoc") as mock_run:
        with pytest.raises(typer.Exit):
            slides_build.run_build(str(src), "-", to="beamer")
    mock_run.assert_not_called()


@pytest.mark.command_graph
def test_run_build_checks_pdf_engine_for_beamer_pdf(tmp_path):
    from pandoc_cli.commands import slides_build

    src = tmp_path / "deck.md"
    src.write_text("# Deck\n", encoding="utf-8")
    out = tmp_path / "deck.pdf"

    with patch.object(slides_build, "find_pdf_engines", return_value=["xelatex"]):
        with patch.object(slides_build, "run_pandoc") as mock_run:
            with patch.object(slides_build, "report_success"):
                slides_build.run_build(str(src), str(out), to="beamer", pdf_engine="xelatex")
    mock_run.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest qa/pandoc/test_slides_commands.py -k "run_build" -v`
Expected: FAIL because `run_build` is not implemented yet.

- [ ] **Step 3: Implement wrapper-level validation and backend delegation**

Update `skill-repo/pandoc/scripts/pandoc_cli/commands/slides_build.py`:

```python
def _is_pdf_path(output: str) -> bool:
    if output == "-":
        return False
    return Path(output).suffix.lower() == ".pdf"


def run_build(
    input: str,
    output: str,
    *,
    to: str,
    from_: Optional[str] = None,
    slide_level: Optional[int] = None,
    incremental: bool = False,
    standalone: Optional[bool] = None,
    toc: bool = False,
    metadata: Optional[list[str]] = None,
    variable: Optional[list[str]] = None,
    pdf_engine: Optional[str] = None,
    embed_resources: bool = False,
) -> None:
    input_path = Path(input)
    if not input_path.exists():
        typer.echo(f"ERROR: Input file not found: {input}", err=True)
        raise typer.Exit(code=1)

    if to not in _SLIDE_WRITERS:
        typer.echo(
            "ERROR: --to must be one of: beamer, revealjs",
            err=True,
        )
        raise typer.Exit(code=1)

    if to == "beamer" and embed_resources:
        typer.echo(
            "ERROR: --embed-resources is only supported for revealjs slide output.",
            err=True,
        )
        raise typer.Exit(code=1)

    if to == "revealjs" and pdf_engine is not None:
        typer.echo(
            "ERROR: --pdf-engine is only supported for beamer slide output.",
            err=True,
        )
        raise typer.Exit(code=1)

    if output == "-" and to == "beamer":
        typer.echo(
            "ERROR: Cannot write beamer slide output to stdout. Use a file path.",
            err=True,
        )
        raise typer.Exit(code=1)

    if pdf_engine is not None:
        available = find_pdf_engines()
        if pdf_engine not in available:
            available_str = ", ".join(available) if available else "(none found)"
            typer.echo(
                f"ERROR: PDF engine '{pdf_engine}' not found on PATH. Available: {available_str}",
                err=True,
            )
            raise typer.Exit(code=1)

    if to == "beamer" and _is_pdf_path(output):
        engines = find_pdf_engines()
        if not engines:
            typer.echo(
                "ERROR: PDF output requested but no PDF engine found on PATH.",
                err=True,
            )
            raise typer.Exit(code=1)

    args = build_args(
        input,
        output,
        to=to,
        from_=from_,
        slide_level=slide_level,
        incremental=incremental,
        standalone=standalone,
        toc=toc,
        metadata=metadata,
        variable=variable,
        pdf_engine=pdf_engine,
        embed_resources=embed_resources,
    )

    result = run_pandoc(args, check=True, capture=True)

    if output == "-":
        if result.stdout:
            typer.echo(result.stdout, nl=False)
    else:
        report_success(output)
```

- [ ] **Step 4: Run the validation tests to verify they pass**

Run: `pytest qa/pandoc/test_slides_commands.py -k "run_build" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skill-repo/pandoc/scripts/pandoc_cli/commands/slides_build.py qa/pandoc/test_slides_commands.py
git commit -m "feat: validate pandoc slides workflows"
```

## Task 4: Add End-To-End Integration Coverage

**Files:**
- Create: `qa/pandoc/test_slides_integration.py`
- Test: `qa/pandoc/test_slides_integration.py`

- [ ] **Step 1: Write the integration tests**

Create `qa/pandoc/test_slides_integration.py`:

```python
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from _pandoc_helpers import assert_html_doctype, assert_pdf_magic


pytestmark = pytest.mark.integration


@pytest.fixture
def runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


@pytest.fixture
def app(pandoc_path):
    from pandoc_cli import app as _app

    return _app


def test_revealjs_build_generates_html_deck(runner, app, simple_md, tmp_path):
    out = tmp_path / "deck.html"

    result = runner.invoke(
        app,
        [
            "slides",
            "build",
            str(simple_md),
            str(out),
            "--to",
            "revealjs",
            "--standalone",
        ],
    )

    assert result.exit_code == 0, result.stderr or result.output
    assert_html_doctype(out)
    text = out.read_text(encoding="utf-8").lower()
    assert "reveal" in text
    assert "<section" in text


def test_beamer_build_generates_pdf_deck(runner, app, simple_md, tmp_path, latex_engine):
    out = tmp_path / "deck.pdf"

    result = runner.invoke(
        app,
        [
            "slides",
            "build",
            str(simple_md),
            str(out),
            "--to",
            "beamer",
            "--pdf-engine",
            latex_engine,
        ],
    )

    assert result.exit_code == 0, result.stderr or result.output
    assert_pdf_magic(out)


def test_revealjs_rejects_pdf_engine(runner, app, simple_md, tmp_path):
    out = tmp_path / "deck.html"

    result = runner.invoke(
        app,
        [
            "slides",
            "build",
            str(simple_md),
            str(out),
            "--to",
            "revealjs",
            "--pdf-engine",
            "xelatex",
        ],
    )

    assert result.exit_code == 1
    combined = (result.stderr or "") + (result.output or "")
    assert "pdf-engine" in combined.lower()
    assert "beamer" in combined.lower()
```

- [ ] **Step 2: Run the integration tests to verify initial failures**

Run: `pytest qa/pandoc/test_slides_integration.py -v`
Expected: initial failures until the CLI group and command logic are fully wired.

- [ ] **Step 3: Fix any integration mismatches without broadening scope**

Use the existing slides implementation only. Do not add extra slide flags or writers during this step. Only correct:

- CLI wiring mistakes
- help/argument declaration issues
- output verification mismatches
- reveal.js or beamer-specific validation mismatches

- [ ] **Step 4: Run the integration tests to verify they pass**

Run: `pytest qa/pandoc/test_slides_integration.py -v`
Expected: PASS, with clean skips only when LaTeX support is absent.

- [ ] **Step 5: Commit**

```bash
git add qa/pandoc/test_slides_integration.py skill-repo/pandoc/scripts/pandoc_cli/slides.py skill-repo/pandoc/scripts/pandoc_cli/commands/slides_build.py
git commit -m "test: add pandoc slides integration coverage"
```

## Task 5: Document The New Slides Workflow

**Files:**
- Create: `skill-repo/pandoc/references/techniques/slides.md`
- Modify: `skill-repo/pandoc/SKILL.md`
- Modify: `skill-repo/pandoc/references/index.md`
- Modify: `skill-repo/pandoc/references/future-scope.md`
- Modify: `qa/pandoc/playbook.md`

- [ ] **Step 1: Write the Slides technique page**

Create `skill-repo/pandoc/references/techniques/slides.md`:

```markdown
# Slides

Build slide decks with the dedicated slides workflow:

```bash
uv run pandoc_cli.py slides build talk.md talk.html --to revealjs --standalone
uv run pandoc_cli.py slides build talk.md talk.pdf --to beamer --pdf-engine xelatex
```

## Supported writers

- `revealjs`
- `beamer`

## Supported wrapper flags

- `--from`
- `--slide-level`
- `--incremental`
- `--standalone`
- `--toc`
- `--metadata`
- `--variable`
- `--pdf-engine` for `beamer`
- `--embed-resources` for `revealjs`

## Customization

Writer-specific customization stays intentionally thin in the wrapper. Use
repeatable `--variable KEY=VALUE` options for writer/template variables such as
themes and layout knobs.

## Gotchas

- `--embed-resources` is rejected for `beamer`
- `--pdf-engine` is rejected for `revealjs`
- `beamer` output cannot be written to stdout
- older slide writers remain deferred
```

- [ ] **Step 2: Update `SKILL.md`**

Change the deferred statement and command list in `skill-repo/pandoc/SKILL.md` to:

```markdown
**slides** — Slide deck generation
- `slides build INPUT OUTPUT --to beamer|revealjs` — build a slide deck using the dedicated slide workflow
```

And replace the old deferred sentence with:

```markdown
Slides are supported for `beamer` and `revealjs`. Older slide writers
(`slidy`, `s5`, `dzslides`, `slideous`) and deeper slide-specific helpers
remain deferred.
```

- [ ] **Step 3: Update the wiki index and future scope**

Update `skill-repo/pandoc/references/index.md`:

```markdown
- [Slides](techniques/slides.md) — build reveal.js HTML decks and beamer PDF decks
```

And revise the deferred summary to:

```markdown
- Older slide writers (slidy, S5, DZSlides, slideous)
```

Update `skill-repo/pandoc/references/future-scope.md` by removing `beamer` and `revealjs` from the top slide backlog and narrowing it to:

```markdown
Older HTML slide writers remain deferred:
- `slidy`
- `s5`
- `dzslides`
- `slideous`

Deeper slide-specific helpers also remain deferred:
- Speaker notes helpers
- Background-image helpers
- Two-column layout helpers
- Named theme/transition wrapper flags
```

- [ ] **Step 4: Add the playbook contract**

Append to `qa/pandoc/playbook.md`:

```markdown
## slides group

### `slides build`

**Signature:**
```bash
pandoc-cli slides build INPUT OUTPUT
  --to beamer|revealjs
  [--from FORMAT]
  [--slide-level N]
  [--incremental]
  [--standalone / --no-standalone]
  [--toc]
  [--metadata KEY=VALUE]
  [--variable KEY=VALUE]
  [--pdf-engine ENGINE]
  [--embed-resources]
```

**Behavior:** Builds slide-deck output using the dedicated slides workflow.
Supports only `beamer` and `revealjs`. Shared options are forwarded directly
to pandoc. Wrapper-level validation rejects incompatible combinations.

**Verification:**
- reveal.js output: standalone HTML with slide-section markers
- beamer output: PDF magic when a LaTeX engine is available

**Edge cases:**
- invalid `--to` value
- `beamer` + `--embed-resources`
- `revealjs` + `--pdf-engine`
- `OUTPUT == "-"` for `beamer`
```

- [ ] **Step 5: Run targeted checks and commit**

Run:

```bash
pytest qa/pandoc/test_slides_commands.py qa/pandoc/test_slides_integration.py -v
```

Expected: PASS

Commit:

```bash
git add skill-repo/pandoc/SKILL.md skill-repo/pandoc/references/index.md skill-repo/pandoc/references/future-scope.md skill-repo/pandoc/references/techniques/slides.md qa/pandoc/playbook.md
git commit -m "docs: document pandoc slides workflow"
```

## Task 6: Final Verification

**Files:**
- Verify only

- [ ] **Step 1: Run the full pandoc QA slice**

Run: `pytest qa/pandoc -v`
Expected: PASS, with clean skips only for environment-dependent integration cases such as missing LaTeX engines.

- [ ] **Step 2: Run a quick CLI smoke check**

Run:

```bash
uv run --project skill-repo/pandoc/scripts pandoc_cli.py slides --help
uv run --project skill-repo/pandoc/scripts pandoc_cli.py slides build --help
```

Expected:

- help output lists the `build` command
- `slides build --help` shows only the agreed MVP flags

- [ ] **Step 3: Review spec coverage**

Check the approved spec at `docs/superpowers/specs/2026-04-21-pandoc-slides-design.md` and confirm all requirements are implemented:

- dedicated `slides` group
- single `build` command
- only `beamer` and `revealjs`
- wrapper-level validation rules
- Tier 1 and Tier 2 coverage
- docs and deferred-scope updates

- [ ] **Step 4: Commit any final cleanup**

```bash
git add .
git commit -m "chore: finalize pandoc slides support"
```

- [ ] **Step 5: Stop and report**

Report:

- commands added
- tests run
- any clean skips due to local environment
- remaining deferred slide features
