"""Logic for list-models command — enumerate available Demucs models.

The installed demucs 4.0.1 doesn't have a --list-models CLI flag.
Instead, we find the demucs package's remote/ directory and list the
YAML model configs directly.
"""

from pathlib import Path


# Known pretrained models with descriptions (from Demucs docs)
MODEL_DESCRIPTIONS = {
    "htdemucs": "Hybrid Transformer Demucs v4 (default, 4 stems)",
    "htdemucs_ft": "Fine-tuned HTDemucs v4 (best quality, 4x slower)",
    "htdemucs_6s": "6-stem HTDemucs (drums, bass, other, vocals, piano, guitar)",
    "hdemucs_mmi": "Hybrid Demucs v3 (legacy)",
    "mdx": "MDX challenge model (4 stems)",
    "mdx_extra": "MDX with extra training data (broader coverage)",
    "mdx_q": "MDX quantized (50% smaller download, requires diffq)",
    "mdx_extra_q": "MDX extra quantized (best size/quality ratio, requires diffq)",
    "repro_mdx_a": "Reproduction of MDX-A submission",
    "repro_mdx_a_hybrid_only": "MDX-A reproduction, hybrid branch only",
    "repro_mdx_a_time_only": "MDX-A reproduction, time branch only",
}


def find_model_configs() -> list[str]:
    """Find available model names from the demucs package's remote/ dir.

    Searches common install locations for the demucs package, then lists
    YAML files in its remote/ subdirectory.
    """
    # Try importing demucs to find its location
    import subprocess
    import sys

    # Try multiple Python executables to find where demucs is installed
    for python in _python_candidates():
        try:
            result = subprocess.run(
                [
                    python, "-c",
                    "import demucs.pretrained; "
                    "from pathlib import Path; "
                    "remote = Path(demucs.pretrained.__file__).parent / 'remote'; "
                    "print(str(remote))",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (FileNotFoundError, OSError):
            continue
        if result.returncode == 0:
            remote_dir = Path(result.stdout.strip())
            if remote_dir.is_dir():
                return sorted(f.stem for f in remote_dir.glob("*.yaml"))

    return []


def _python_candidates() -> list[str]:
    """Return Python executable candidates to try.

    Demucs may be installed in a different Python than the one running
    this CLI (which runs in a uv venv). We try multiple locations.
    """
    import sys
    import shutil

    candidates = [sys.executable]

    # Try 'python' and 'python3' from PATH
    for name in ("python", "python3"):
        path = shutil.which(name)
        if path and path not in candidates:
            candidates.append(path)

    # On Windows, try common system Python locations
    if sys.platform == "win32":
        from pathlib import Path as P

        for loc in [
            P("C:/Python313/python.exe"),
            P("C:/Python312/python.exe"),
            P("C:/Python311/python.exe"),
        ]:
            if loc.exists() and str(loc) not in candidates:
                candidates.append(str(loc))

        # Also try the Python that the demucs executable was installed with
        demucs_exe = shutil.which("demucs")
        if demucs_exe:
            demucs_dir = P(demucs_exe).parent
            for python_exe in demucs_dir.glob("python*.exe"):
                p = str(python_exe)
                if p not in candidates:
                    candidates.append(p)

    return candidates


def build_output() -> str:
    """Build the formatted model list output."""
    models = find_model_configs()
    if not models:
        return "No models found. Is demucs installed? pip install demucs"

    lines = ["Available Demucs models:", ""]
    for name in models:
        desc = MODEL_DESCRIPTIONS.get(name, "")
        if desc:
            lines.append(f"  {name:<25} {desc}")
        else:
            lines.append(f"  {name}")
    return "\n".join(lines)
