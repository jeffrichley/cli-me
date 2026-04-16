from pathlib import Path

from cli_me.log import LogFile


def test_append_to_existing_log(tmp_path):
    """append() adds an entry to an existing log file."""
    log_path = tmp_path / "log.md"
    log_path.write_text("# Log\n\n---\n")

    log = LogFile(log_path)
    log.append("inkscape", "Learned that inkscape CLI needs --batch flag.")

    content = log_path.read_text()
    assert "inkscape" in content
    assert "--batch flag" in content


def test_append_creates_file_if_missing(tmp_path):
    """append() creates the log file if it doesn't exist."""
    log_path = tmp_path / "log.md"

    log = LogFile(log_path)
    log.append("blender", "Blender needs --background for headless mode.")

    assert log_path.exists()
    content = log_path.read_text()
    assert "blender" in content
    assert "--background" in content


def test_append_preserves_existing_content(tmp_path):
    """append() does not overwrite existing log entries."""
    log_path = tmp_path / "log.md"
    log_path.write_text("# Log\n\nExisting entry here.\n")

    log = LogFile(log_path)
    log.append("gimp", "GIMP needs --no-interface for CLI mode.")

    content = log_path.read_text()
    assert "Existing entry here." in content
    assert "GIMP needs --no-interface" in content


def test_append_includes_date(tmp_path):
    """append() includes a date in the entry."""
    log_path = tmp_path / "log.md"

    log = LogFile(log_path)
    log.append("test-skill", "Some learning.")

    content = log_path.read_text()
    # Should contain a date in ISO format (YYYY-MM-DD)
    import re
    assert re.search(r"\d{4}-\d{2}-\d{2}", content)


def test_multiple_appends_are_ordered(tmp_path):
    """Multiple appends appear in order."""
    log_path = tmp_path / "log.md"

    log = LogFile(log_path)
    log.append("first", "First entry.")
    log.append("second", "Second entry.")
    log.append("third", "Third entry.")

    content = log_path.read_text()
    pos_first = content.index("First entry.")
    pos_second = content.index("Second entry.")
    pos_third = content.index("Third entry.")
    assert pos_first < pos_second < pos_third
