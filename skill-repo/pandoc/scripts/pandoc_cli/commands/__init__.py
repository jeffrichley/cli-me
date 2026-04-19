"""Logic-layer functions, independently testable without Typer.

Each command-group dispatch module (../convert.py, ../citations.py, etc.)
imports its logic from here. Tests import from here directly without going
through CliRunner.
"""
