"""Backend utilities for Demucs CLI — find executable, detect version, device, run commands."""

import shutil
import subprocess
import sys

import typer


def find_executable(name: str = "demucs") -> str:
    """Find the demucs executable or exit with install instructions."""
    path = shutil.which(name)
    if path is not None:
        return path

    # Windows: check common pip install locations not on PATH
    if sys.platform == "win32":
        import pathlib

        for scripts_dir in pathlib.Path.home().glob(
            "AppData/Roaming/Python/Python3*/Scripts"
        ):
            candidate = scripts_dir / f"{name}.exe"
            if candidate.exists():
                return str(candidate)
        for scripts_dir in pathlib.Path.home().glob(
            "AppData/Local/Programs/Python/Python3*/Scripts"
        ):
            candidate = scripts_dir / f"{name}.exe"
            if candidate.exists():
                return str(candidate)

    typer.echo(
        f"ERROR: {name} not found. Install with: pip install demucs\n"
        f"Or see: https://github.com/facebookresearch/demucs#requirements",
        err=True,
    )
    raise typer.Exit(code=1)


def detect_version() -> str:
    """Detect installed demucs version string."""
    result = subprocess.run(
        [sys.executable, "-c", "import demucs; print(demucs.__version__)"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip()


def _find_demucs_python() -> str:
    """Find the Python interpreter that has demucs installed.

    The CLI runs in a uv venv, but demucs may be installed in a different
    system Python. This finds the right one for torch/device checks.
    """
    # Try the Python next to the demucs executable first
    from pathlib import Path

    demucs_exe = shutil.which("demucs")
    if demucs_exe:
        demucs_dir = Path(demucs_exe).parent
        for name in ("python.exe", "python3.exe", "python"):
            candidate = demucs_dir / name
            if candidate.exists():
                return str(candidate)

    # Try system Python candidates
    for name in ("python", "python3"):
        path = shutil.which(name)
        if path:
            result = subprocess.run(
                [path, "-c", "import demucs"],
                capture_output=True,
                timeout=15,
            )
            if result.returncode == 0:
                return path

    # Windows: try common install locations
    if sys.platform == "win32":
        from pathlib import Path as P

        for loc in P("C:/").glob("Python3*/python.exe"):
            result = subprocess.run(
                [str(loc), "-c", "import demucs"],
                capture_output=True,
                timeout=15,
            )
            if result.returncode == 0:
                return str(loc)

    return sys.executable


def detect_device() -> str:
    """Auto-detect the best available compute device.

    Checks CUDA first, then MPS (Apple Silicon), then falls back to CPU.
    Uses the same Python that has demucs installed (not the uv venv Python).
    """
    python = _find_demucs_python()
    result = subprocess.run(
        [
            python,
            "-c",
            "import torch; "
            "print('cuda' if torch.cuda.is_available() "
            "else 'mps' if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available() "
            "else 'cpu')",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return "cpu"
    return result.stdout.strip()


def run_command(
    args: list[str],
    check: bool = True,
    capture: bool = False,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    """Run a demucs command and return the result.

    Args:
        args: Arguments to pass to demucs (without the executable name).
        check: Raise on non-zero exit code.
        capture: Capture stdout/stderr instead of streaming.
        timeout: Timeout in seconds (None = no timeout).
    """
    exe = find_executable()
    cmd = [exe] + args
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
        timeout=timeout,
    )
