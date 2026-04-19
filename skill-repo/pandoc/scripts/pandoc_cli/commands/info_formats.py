"""Logic for `info formats` — list pandoc input/output formats."""

from __future__ import annotations

from typing import Literal

from pandoc_cli.backend import run_pandoc

Side = Literal["both", "input", "output"]


def _list_formats(flag: str) -> list[str]:
    """Run `pandoc <flag>` and return the parsed (non-blank, stripped) lines."""
    result = run_pandoc([flag], check=True, capture=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def run_formats(side: Side = "both") -> dict[str, list[str]]:
    """Return pandoc's input and/or output format lists.

    Parameters
    ----------
    side
        ``"both"``   — populate both ``input`` and ``output``.
        ``"input"``  — populate ``input`` only; ``output`` is ``[]``.
        ``"output"`` — populate ``output`` only; ``input`` is ``[]``.

    Returns
    -------
    dict
        ``{"input": [...], "output": [...]}``. Lists are pandoc's order.

    Raises
    ------
    ValueError
        If ``side`` is not one of ``"both"``, ``"input"``, ``"output"``.
    """
    if side not in ("both", "input", "output"):
        raise ValueError(
            f"Invalid side {side!r}; expected 'both', 'input', or 'output'."
        )

    inputs: list[str] = []
    outputs: list[str] = []
    if side in ("both", "input"):
        inputs = _list_formats("--list-input-formats")
    if side in ("both", "output"):
        outputs = _list_formats("--list-output-formats")

    return {"input": inputs, "output": outputs}
