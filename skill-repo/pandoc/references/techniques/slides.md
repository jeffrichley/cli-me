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
