"""Locked append-only log file for concurrent agent writes."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from cli_me.filelock import locked_write


class LogFile:
    """Append-only markdown log with file locking."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def append(self, skill: str, message: str) -> None:
        """Append a timestamped entry to the log.

        Uses file locking so multiple agents can safely append concurrently.
        """
        today = date.today().isoformat()
        entry = f"\n**{today}** [{skill}] — {message}\n"

        def writer(path: Path) -> None:
            if self.path.exists():
                existing = self.path.read_text()
            else:
                existing = "# Log\n"
            path.write_text(existing + entry)

        locked_write(self.path, writer)
