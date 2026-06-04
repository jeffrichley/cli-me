"""Tier 2 integration tests for gimp-cli against real GIMP binary."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skill-repo" / "gimp" / "scripts"))

from gimp_cli import app  # noqa: E402


@pytest.mark.integration
def test_gimp_version_reports_semantic_tokens(gimp_path: str) -> None:
    result = subprocess.run([gimp_path, "--version"], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()
    assert "GNU Image Manipulation Program" in result.stdout
    assert "version" in result.stdout.lower()


@pytest.mark.integration
def test_gimp_batch_quit_noninteractive(gimp_path: str) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["batch", "run", "--command", "(gimp-quit 0)"])
    assert result.exit_code == 0, result.output


@pytest.mark.integration
def test_info_capabilities_prints_binary_and_flags(gimp_path: str) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["info", "capabilities"])
    assert result.exit_code == 0, result.output
    assert "binary:" in result.output
    assert gimp_path in result.output
    assert "--batch" in result.output
    assert "--batch-interpreter" in result.output


@pytest.mark.integration
def test_pod_resize_generates_expected_dimensions(tmp_path: Path) -> None:
    src = tmp_path / "src.png"
    out = tmp_path / "out.png"
    Image.new("RGBA", (1000, 1000), (255, 0, 0, 255)).save(src)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "pod",
            "resize",
            "--input",
            str(src),
            "--output",
            str(out),
            "--width",
            "4500",
            "--height",
            "5400",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    with Image.open(out) as image:
        assert image.size == (4500, 5400)
