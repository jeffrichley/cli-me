"""Tier 3 manual checks for gimp-cli."""

from __future__ import annotations

import pytest


@pytest.mark.manual
def test_manual_batch_expression_review(gimp_path: str, capsys) -> None:
    print("Manual check:")
    print(f"- Binary detected: {gimp_path}")
    print("- Run: uv run skill-repo/gimp/scripts/gimp_cli.py batch run --command \"(gimp-quit 0)\"")
    print("- Confirm command exits quickly and prints no GUI dialog.")
    captured = capsys.readouterr()
    assert "Manual check:" in captured.out
