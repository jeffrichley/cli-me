"""Tier 1: filters command logic tests — mocked, no real pandoc binary needed.

Exercises ``run_apply``, ``build_args``, and ``run_crossref_check`` in
``pandoc_cli.commands.filters_*`` directly. Mocks the backend / subprocess /
shutil layer so the suite runs deterministically with no dependency on pandoc
or pandoc-crossref being installed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import typer


# ---------------------------------------------------------------------------
# build_args (filters apply)
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestBuildArgs:
    def test_no_filters_emits_just_input_and_output(self):
        from pandoc_cli.commands import filters_apply

        args = filters_apply.build_args(
            input_path="in.md",
            output_path="out.html",
            ordered_filters=[],
        )
        assert args == ["in.md", "-o", "out.html"]

    def test_single_lua_filter(self):
        from pandoc_cli.commands import filters_apply

        args = filters_apply.build_args(
            input_path="in.md",
            output_path="out.html",
            ordered_filters=[("lua", "p.lua")],
        )
        assert "--lua-filter" in args
        i = args.index("--lua-filter")
        assert args[i + 1] == "p.lua"
        # input + -o + output + --lua-filter + path = 5 tokens
        assert args == ["in.md", "-o", "out.html", "--lua-filter", "p.lua"]

    def test_multiple_lua_filters_preserve_order(self):
        from pandoc_cli.commands import filters_apply

        args = filters_apply.build_args(
            input_path="in.md",
            output_path="out.html",
            ordered_filters=[("lua", "first.lua"), ("lua", "second.lua")],
        )
        # Both filter paths should appear, first.lua before second.lua
        assert "first.lua" in args
        assert "second.lua" in args
        assert args.index("first.lua") < args.index("second.lua")

    def test_mixed_lua_and_json_preserve_cli_order_lua_first(self):
        from pandoc_cli.commands import filters_apply

        args = filters_apply.build_args(
            input_path="in.md",
            output_path="out.html",
            ordered_filters=[
                ("lua", "alpha.lua"),
                ("json", "beta-bin"),
                ("lua", "gamma.lua"),
            ],
        )
        # CLI order alpha → beta → gamma must appear as that order in argv,
        # each preceded by the correct flag.
        idx_alpha = args.index("alpha.lua")
        idx_beta = args.index("beta-bin")
        idx_gamma = args.index("gamma.lua")
        assert idx_alpha < idx_beta < idx_gamma
        assert args[idx_alpha - 1] == "--lua-filter"
        assert args[idx_beta - 1] == "--filter"
        assert args[idx_gamma - 1] == "--lua-filter"

    def test_mixed_lua_and_json_preserve_cli_order_json_first(self):
        from pandoc_cli.commands import filters_apply

        args = filters_apply.build_args(
            input_path="in.md",
            output_path="out.html",
            ordered_filters=[
                ("json", "x-bin"),
                ("lua", "y.lua"),
            ],
        )
        idx_x = args.index("x-bin")
        idx_y = args.index("y.lua")
        assert idx_x < idx_y
        assert args[idx_x - 1] == "--filter"
        assert args[idx_y - 1] == "--lua-filter"

    def test_extra_flags_appended(self):
        from pandoc_cli.commands import filters_apply

        args = filters_apply.build_args(
            input_path="in.md",
            output_path="out.html",
            ordered_filters=[("lua", "p.lua")],
            extra=["--standalone", "--from", "markdown"],
        )
        assert "--standalone" in args
        assert "--from" in args
        assert args[args.index("--from") + 1] == "markdown"


# ---------------------------------------------------------------------------
# run_apply
# ---------------------------------------------------------------------------


def _fake_completed(returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


@pytest.mark.command_graph
class TestRunApply:
    def test_input_missing_exits_1(self, tmp_path: Path):
        from pandoc_cli.commands import filters_apply

        missing = tmp_path / "no-such.md"
        with pytest.raises(typer.Exit) as exc:
            filters_apply.run_apply(
                input_path=missing,
                output_path=tmp_path / "out.html",
                ordered_filters=[],
            )
        assert exc.value.exit_code == 1

    def test_lua_filter_missing_exits_1_before_invoking_pandoc(self, tmp_path: Path):
        from pandoc_cli.commands import filters_apply

        inp = tmp_path / "in.md"
        inp.write_text("# x\n", encoding="utf-8")
        missing_filter = tmp_path / "missing.lua"

        with patch.object(filters_apply, "run_pandoc") as fake_run:
            with pytest.raises(typer.Exit) as exc:
                filters_apply.run_apply(
                    input_path=inp,
                    output_path=tmp_path / "out.html",
                    ordered_filters=[("lua", str(missing_filter))],
                )
            assert exc.value.exit_code == 1
            # pandoc must not be invoked when validation fails
            fake_run.assert_not_called()

    def test_json_filter_missing_exits_1_before_invoking_pandoc(self, tmp_path: Path):
        from pandoc_cli.commands import filters_apply

        inp = tmp_path / "in.md"
        inp.write_text("# x\n", encoding="utf-8")
        missing_filter = tmp_path / "missing-bin"

        with patch.object(filters_apply, "run_pandoc") as fake_run:
            with pytest.raises(typer.Exit) as exc:
                filters_apply.run_apply(
                    input_path=inp,
                    output_path=tmp_path / "out.html",
                    ordered_filters=[("json", str(missing_filter))],
                )
            assert exc.value.exit_code == 1
            fake_run.assert_not_called()

    def test_all_preconditions_met_invokes_pandoc_with_correct_argv(
        self, tmp_path: Path
    ):
        from pandoc_cli.commands import filters_apply

        inp = tmp_path / "in.md"
        inp.write_text("# x\n", encoding="utf-8")
        flt1 = tmp_path / "a.lua"
        flt1.write_text("-- noop\n", encoding="utf-8")
        flt2 = tmp_path / "b.lua"
        flt2.write_text("-- noop\n", encoding="utf-8")

        captured: list = []

        def fake_run_pandoc(args, *, check=True, capture=True, **_kwargs):
            captured.append(list(args))
            return _fake_completed()

        with patch.object(filters_apply, "run_pandoc", side_effect=fake_run_pandoc):
            filters_apply.run_apply(
                input_path=inp,
                output_path=tmp_path / "out.html",
                ordered_filters=[("lua", str(flt1)), ("lua", str(flt2))],
            )

        assert len(captured) == 1
        argv = captured[0]
        assert str(inp) in argv
        assert "-o" in argv
        # Both filter paths present in CLI order
        assert argv.index(str(flt1)) < argv.index(str(flt2))

    def test_extra_flags_forwarded(self, tmp_path: Path):
        from pandoc_cli.commands import filters_apply

        inp = tmp_path / "in.md"
        inp.write_text("# x\n", encoding="utf-8")

        captured: list = []

        def fake_run_pandoc(args, *, check=True, capture=True, **_kwargs):
            captured.append(list(args))
            return _fake_completed()

        with patch.object(filters_apply, "run_pandoc", side_effect=fake_run_pandoc):
            filters_apply.run_apply(
                input_path=inp,
                output_path=tmp_path / "out.html",
                ordered_filters=[],
                extra=["--standalone"],
            )

        assert "--standalone" in captured[0]


# ---------------------------------------------------------------------------
# run_crossref_check
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunCrossrefCheck:
    def test_missing_pandoc_crossref_exits_1(self):
        from pandoc_cli.commands import filters_crossref
        from pandoc_cli import backend

        # check_pandoc_crossref calls shutil.which under the hood; mock that.
        with patch.object(backend.shutil, "which", return_value=None):
            with pytest.raises(typer.Exit) as exc:
                filters_crossref.run_crossref_check()
            assert exc.value.exit_code == 1

    def test_present_returns_path_and_version(self):
        from pandoc_cli.commands import filters_crossref
        from pandoc_cli import backend

        fake_path = "/fake/bin/pandoc-crossref"
        mocked_stdout = "pandoc-crossref v0.3.17.0\n"
        captured_calls: list[list[str]] = []

        def fake_subproc_run(cmd, *args, **kwargs):
            captured_calls.append(list(cmd))
            return _fake_completed(stdout=mocked_stdout)

        with patch.object(backend.shutil, "which", return_value=fake_path):
            with patch.object(
                filters_crossref.subprocess, "run", side_effect=fake_subproc_run
            ):
                result = filters_crossref.run_crossref_check()

        # The version probe must be exactly [fake_path, "--version"] — no
        # extra flags, no different ordering. R4 lockdown: prevents silent
        # regressions where the call shape drifts (e.g. someone adds
        # ``--numeric-version`` and breaks downstream parsing).
        assert captured_calls == [[fake_path, "--version"]]
        assert result["path"] == fake_path
        # Version must equal the EXACT mocked stdout (stripped), not just
        # contain a substring — this guards against a refactor that returns
        # only a parsed semver and drops the build metadata.
        assert result["version"] == mocked_stdout.strip()

    def test_present_but_empty_version_exits_1(self):
        """R3#3: empty `--version` output is a corruption signal — surface it."""
        from pandoc_cli.commands import filters_crossref
        from pandoc_cli import backend

        fake_path = "/fake/bin/pandoc-crossref"

        def fake_subproc_run(cmd, *args, **kwargs):
            # Both stdout and stderr empty — the documented failure mode.
            return _fake_completed(stdout="", stderr="")

        with patch.object(backend.shutil, "which", return_value=fake_path):
            with patch.object(
                filters_crossref.subprocess, "run", side_effect=fake_subproc_run
            ):
                with pytest.raises(typer.Exit) as exc:
                    filters_crossref.run_crossref_check()

        assert exc.value.exit_code == 1


# ---------------------------------------------------------------------------
# _ordered_filters_from_argv — direct unit tests (R4 must-fix)
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestOrderedFiltersFromArgv:
    """Walker is the most fragile piece of filter dispatch — exhaustive coverage
    of all 4 argv forms plus interleaved order plus the empty-argv fallback."""

    def test_lua_filter_space_form(self):
        from pandoc_cli.filters import _ordered_filters_from_argv

        argv = ["pandoc_cli", "filters", "apply", "in.md", "out.html",
                "--lua-filter", "a.lua"]
        assert _ordered_filters_from_argv(argv, [], []) == [("lua", "a.lua")]

    def test_lua_filter_equals_form(self):
        from pandoc_cli.filters import _ordered_filters_from_argv

        argv = ["pandoc_cli", "filters", "apply", "in.md", "out.html",
                "--lua-filter=a.lua"]
        assert _ordered_filters_from_argv(argv, [], []) == [("lua", "a.lua")]

    def test_json_filter_space_form(self):
        from pandoc_cli.filters import _ordered_filters_from_argv

        argv = ["pandoc_cli", "filters", "apply", "in.md", "out.html",
                "--filter", "b-bin"]
        assert _ordered_filters_from_argv(argv, [], []) == [("json", "b-bin")]

    def test_json_filter_equals_form(self):
        from pandoc_cli.filters import _ordered_filters_from_argv

        argv = ["pandoc_cli", "filters", "apply", "in.md", "out.html",
                "--filter=b-bin"]
        assert _ordered_filters_from_argv(argv, [], []) == [("json", "b-bin")]

    def test_interleaved_lua_json_lua_preserves_order(self):
        from pandoc_cli.filters import _ordered_filters_from_argv

        argv = ["--lua-filter", "a.lua", "--filter", "b", "--lua-filter", "c.lua"]
        assert _ordered_filters_from_argv(argv, [], []) == [
            ("lua", "a.lua"),
            ("json", "b"),
            ("lua", "c.lua"),
        ]

    def test_mixed_space_and_equals_forms(self):
        from pandoc_cli.filters import _ordered_filters_from_argv

        argv = ["--lua-filter=a.lua", "--filter", "b", "--lua-filter", "c.lua",
                "--filter=d"]
        assert _ordered_filters_from_argv(argv, [], []) == [
            ("lua", "a.lua"),
            ("json", "b"),
            ("lua", "c.lua"),
            ("json", "d"),
        ]

    def test_empty_argv_with_fallback_lists_returns_lua_first(self):
        """Documented programmatic-invocation fallback — lua before json
        (interleaving is LOST). See docstring on _ordered_filters_from_argv."""
        from pandoc_cli.filters import _ordered_filters_from_argv

        result = _ordered_filters_from_argv([], ["a.lua", "b.lua"], ["x", "y"])
        assert result == [
            ("lua", "a.lua"),
            ("lua", "b.lua"),
            ("json", "x"),
            ("json", "y"),
        ]

    def test_empty_everything_returns_empty_list(self):
        from pandoc_cli.filters import _ordered_filters_from_argv

        assert _ordered_filters_from_argv([], [], []) == []

    def test_path_containing_lua_filter_substring_not_matched_as_flag(self):
        """Token-equality (not substring) match: a path like ``my--lua-filter.lua``
        must NOT be parsed as the flag itself."""
        from pandoc_cli.filters import _ordered_filters_from_argv

        argv = ["--lua-filter", "weird--lua-filter-name.lua"]
        assert _ordered_filters_from_argv(argv, [], []) == [
            ("lua", "weird--lua-filter-name.lua"),
        ]

    def test_dangling_flag_without_value_is_ignored(self):
        """Defensive: trailing ``--lua-filter`` with no following token must
        not crash. Typer would normally reject this, but the walker must be
        robust to truncated argv."""
        from pandoc_cli.filters import _ordered_filters_from_argv

        argv = ["in.md", "out.html", "--lua-filter"]
        assert _ordered_filters_from_argv(argv, [], []) == []


# ---------------------------------------------------------------------------
# R3#2 — Lua type-mismatch hint surfaces on __toinline / __toblock errors
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestLuaTypeMismatchHint:
    def test_toinline_in_stderr_appends_hint(self, tmp_path: Path, capsys):
        """When pandoc fails with ``__toinline`` in its stderr, run_apply
        appends the wiki-pointing HINT (the underlying ``run_pandoc`` is
        responsible for forwarding pandoc's own stderr; here we mock that
        layer so we only assert the HINT addition)."""
        from pandoc_cli.commands import filters_apply

        inp = tmp_path / "in.md"
        inp.write_text("# x\n", encoding="utf-8")
        flt = tmp_path / "bad.lua"
        flt.write_text("-- noop\n", encoding="utf-8")

        def fake_run_pandoc(args, *, check=True, capture=True, **_kwargs):
            return _fake_completed(
                returncode=43,
                stderr="Error running filter bad.lua:\n__toinline: ...",
            )

        with patch.object(filters_apply, "run_pandoc", side_effect=fake_run_pandoc):
            with pytest.raises(typer.Exit) as exc:
                filters_apply.run_apply(
                    input_path=inp,
                    output_path=tmp_path / "out.html",
                    ordered_filters=[("lua", str(flt))],
                )

        assert exc.value.exit_code == 43
        captured = capsys.readouterr()
        # The wiki-pointing HINT must be appended.
        assert "Lua filter type mismatch" in captured.err
        assert "Block" in captured.err and "Inline" in captured.err

    def test_toblock_in_stderr_appends_hint(self, tmp_path: Path, capsys):
        from pandoc_cli.commands import filters_apply

        inp = tmp_path / "in.md"
        inp.write_text("# x\n", encoding="utf-8")
        flt = tmp_path / "bad.lua"
        flt.write_text("-- noop\n", encoding="utf-8")

        def fake_run_pandoc(args, *, check=True, capture=True, **_kwargs):
            return _fake_completed(
                returncode=43,
                stderr="Error running filter bad.lua:\n__toblock: ...",
            )

        with patch.object(filters_apply, "run_pandoc", side_effect=fake_run_pandoc):
            with pytest.raises(typer.Exit):
                filters_apply.run_apply(
                    input_path=inp,
                    output_path=tmp_path / "out.html",
                    ordered_filters=[("lua", str(flt))],
                )

        captured = capsys.readouterr()
        assert "Lua filter type mismatch" in captured.err

    def test_unrelated_error_does_not_append_hint(self, tmp_path: Path, capsys):
        """Hint must NOT fire on generic pandoc errors — only on the type
        mismatch. Otherwise users get noise on every failure."""
        from pandoc_cli.commands import filters_apply

        inp = tmp_path / "in.md"
        inp.write_text("# x\n", encoding="utf-8")

        def fake_run_pandoc(args, *, check=True, capture=True, **_kwargs):
            return _fake_completed(
                returncode=1,
                stderr="pandoc: cannot parse format spec 'bogus'",
            )

        with patch.object(filters_apply, "run_pandoc", side_effect=fake_run_pandoc):
            with pytest.raises(typer.Exit):
                filters_apply.run_apply(
                    input_path=inp,
                    output_path=tmp_path / "out.html",
                    ordered_filters=[],
                )

        captured = capsys.readouterr()
        # The HINT must NOT fire on unrelated errors. (Pandoc's own stderr is
        # forwarded by the real ``run_pandoc``, which we mock here.)
        assert "Lua filter type mismatch" not in captured.err
