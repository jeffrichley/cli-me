"""Integration tests for the ffmpeg skill structure and installability."""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from cli_me.main import app as clime_app


runner = CliRunner()
SKILL_DIR = Path(__file__).parent.parent / "skill-repo" / "ffmpeg"


def test_skill_structure_exists():
    """Verify the skill folder has the required structure."""
    assert (SKILL_DIR / "SKILL.md").exists()
    assert (SKILL_DIR / "scripts" / "pyproject.toml").exists()
    assert (SKILL_DIR / "scripts" / "ffmpeg_cli.py").exists()
    assert (SKILL_DIR / "references" / "index.md").exists()
    assert (SKILL_DIR / "references" / "log.md").exists()
    assert (SKILL_DIR / "references" / "gotchas.md").exists()


def test_skill_md_has_frontmatter():
    """Verify SKILL.md has proper YAML frontmatter."""
    content = (SKILL_DIR / "SKILL.md").read_text()
    assert content.startswith("---")
    assert "name: ffmpeg" in content
    assert "description:" in content


def test_all_35_technique_pages_exist():
    """Verify all 35 technique pages were created."""
    techniques = SKILL_DIR / "references" / "techniques"
    expected = [
        "convert-video-format.md", "compress-video.md", "convert-audio-format.md",
        "platform-encoding.md", "hardware-encoding.md", "trim-clip.md",
        "extract-audio.md", "extract-frames.md", "sprite-sheet.md",
        "surveillance-clip.md", "resize-scale.md", "crop-vertical.md",
        "change-speed.md", "watermark-overlay.md", "burn-subtitles.md",
        "rotate-flip.md", "fade-transitions.md", "normalize-loudness.md",
        "remove-silence.md", "denoise-audio.md", "music-ducking.md",
        "concatenate-clips.md", "mux-audio-video.md", "image-sequence-to-video.md",
        "complex-filtergraph.md", "hls-segments.md", "dash-segments.md",
        "multi-bitrate.md", "rtmp-restream.md", "fake-live-stream.md",
        "batch-transcode.md", "ffprobe-validate.md", "rtsp-recording.md",
        "video-to-gif.md", "screen-capture.md",
    ]
    for page in expected:
        assert (techniques / page).exists(), f"Missing technique page: {page}"


def test_technique_pages_have_required_sections():
    """Spot-check that technique pages follow the three-layer structure."""
    techniques = SKILL_DIR / "references" / "techniques"
    for page_path in techniques.glob("*.md"):
        content = page_path.read_text()
        assert "## When to Use" in content, f"{page_path.name} missing 'When to Use'"
        assert "## CLI Commands" in content, f"{page_path.name} missing 'CLI Commands'"
        assert "## Sources" in content, f"{page_path.name} missing 'Sources'"


def test_source_analysis_pages_exist():
    """Verify source analysis pages exist."""
    sa = SKILL_DIR / "references" / "source-analysis"
    assert (sa / "analyzed-version.md").exists()
    assert (sa / "api-surface.md").exists()
    assert (sa / "cli-interface.md").exists()
    assert (sa / "changelog.md").exists()


def test_registry_contains_ffmpeg():
    """Verify ffmpeg is in the registry."""
    registry_path = Path(__file__).parent.parent / "skill-repo" / "registry.json"
    data = json.loads(registry_path.read_text())
    names = [s["name"] for s in data["skills"]]
    assert "ffmpeg" in names


def test_install_ffmpeg_skill(tmp_path):
    """Test installing the ffmpeg skill to a project."""
    result = runner.invoke(clime_app, [
        "install", "ffmpeg", "--project", str(tmp_path)
    ])
    assert result.exit_code == 0
    installed = tmp_path / ".claude" / "skills" / "ffmpeg"
    assert (installed / "SKILL.md").exists()
    assert (installed / "scripts" / "ffmpeg_cli.py").exists()
    assert (installed / "references" / "techniques" / "trim-clip.md").exists()


def test_index_references_all_technique_pages():
    """Verify index.md links to all technique pages."""
    index_content = (SKILL_DIR / "references" / "index.md").read_text()
    techniques = SKILL_DIR / "references" / "techniques"
    for page_path in techniques.glob("*.md"):
        stem = page_path.stem
        assert stem in index_content, f"index.md missing reference to {stem}"
