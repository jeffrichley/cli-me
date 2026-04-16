import json
from pathlib import Path

from cli_me.filelock import locked_write


def test_locked_write_creates_file(tmp_path):
    """locked_write creates the target file if it doesn't exist."""
    target = tmp_path / "data.json"

    def writer(path: Path) -> None:
        path.write_text(json.dumps({"created": True}))

    locked_write(target, writer)

    assert target.exists()
    assert json.loads(target.read_text()) == {"created": True}


def test_locked_write_uses_lock_file(tmp_path):
    """locked_write creates a .lock file next to the target."""
    target = tmp_path / "data.json"
    target.write_text("{}")
    lock_path = target.with_suffix(target.suffix + ".lock")

    locked = False

    def writer(path: Path) -> None:
        nonlocal locked
        locked = lock_path.exists()
        path.write_text("{}")

    locked_write(target, writer)

    # The lock file existed while the writer ran
    assert locked


def test_locked_write_atomic_via_temp(tmp_path):
    """locked_write writes to a temp file then renames, so partial writes
    don't corrupt the target."""
    target = tmp_path / "data.json"
    target.write_text(json.dumps({"original": True}))

    def writer(path: Path) -> None:
        # path is a temp file, not the target
        assert path != target
        path.write_text(json.dumps({"updated": True}))

    locked_write(target, writer, atomic=True)

    assert json.loads(target.read_text()) == {"updated": True}


def test_locked_write_non_atomic_writes_directly(tmp_path):
    """When atomic=False, the writer gets the target path directly."""
    target = tmp_path / "data.json"
    target.write_text("{}")

    def writer(path: Path) -> None:
        assert path == target
        path.write_text(json.dumps({"direct": True}))

    locked_write(target, writer, atomic=False)

    assert json.loads(target.read_text()) == {"direct": True}


def test_locked_write_timeout(tmp_path):
    """locked_write raises Timeout if it can't acquire the lock."""
    from filelock import Timeout

    target = tmp_path / "data.json"
    target.write_text("{}")
    lock_path = target.with_suffix(target.suffix + ".lock")

    from filelock import FileLock

    # Hold the lock externally
    external_lock = FileLock(lock_path)
    external_lock.acquire()

    try:
        raised = False
        try:
            locked_write(target, lambda p: None, timeout=0.1)
        except Timeout:
            raised = True
        assert raised
    finally:
        external_lock.release()
