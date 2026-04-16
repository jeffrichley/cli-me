"""Shared fixtures for pyannote QA tests."""

import sys
from pathlib import Path

# Add the pyannote scripts directory to sys.path so we can import pyannote_cli
scripts_dir = Path(__file__).resolve().parent.parent.parent / "skill-repo" / "pyannote" / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
