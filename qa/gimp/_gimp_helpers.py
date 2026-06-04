from __future__ import annotations


def assert_has_flag_sequence(args: list[str], expected_sequence: list[str]) -> None:
    for item in expected_sequence:
        assert item in args
