"""Logic-layer functions, independently testable without Typer.

Each command-group dispatch (../check.py, ../character.py, etc.) imports
its logic from here. Tests import from here directly. Phase 3 populates
the actual command logic modules.
"""
