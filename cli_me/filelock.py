"""Cross-platform file locking for concurrent access safety."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

from filelock import FileLock


def locked_write(
    target: Path,
    writer: Callable[[Path], None],
    *,
    atomic: bool = True,
    timeout: float = 30.0,
) -> None:
    """Acquire a lock on *target*, run *writer*, release the lock.

    Parameters
    ----------
    target:
        The file to protect. A ``<target>.lock`` file is created next to it.
    writer:
        A callable that receives a Path and writes content to it.
        When *atomic* is True, the path is a temp file that gets renamed
        over *target* after the writer returns.
        When *atomic* is False, the path is *target* itself.
    atomic:
        If True (default), write to a temp file and rename over *target*.
        This prevents partial writes from corrupting the file.
    timeout:
        Seconds to wait for the lock before raising ``filelock.Timeout``.
    """
    lock_path = target.with_suffix(target.suffix + ".lock")
    lock = FileLock(lock_path, timeout=timeout)

    with lock:
        if atomic:
            fd, tmp_path_str = tempfile.mkstemp(
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
            )
            os.close(fd)
            tmp_path = Path(tmp_path_str)
            try:
                writer(tmp_path)
                tmp_path.replace(target)
            except BaseException:
                tmp_path.unlink(missing_ok=True)
                raise
        else:
            writer(target)
