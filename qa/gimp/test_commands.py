"""Tier 1 command-graph tests for gimp-cli."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skill-repo" / "gimp" / "scripts"))

from gimp_cli import app  # noqa: E402
from gimp_cli.commands.batch import build_batch_args  # noqa: E402
from gimp_cli.commands.info import build_version_args, capability_flags  # noqa: E402
from gimp_cli.commands.pod import (  # noqa: E402
    build_fit_crop_expression,
    build_pod_batch_args,
    build_prep_expression,
    build_resize_expression,
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.command_graph
def test_info_build_version_args_exact() -> None:
    assert build_version_args() == ["--version"]


@pytest.mark.command_graph
def test_info_capability_flags_include_core_batch_flags() -> None:
    flags = capability_flags()
    assert "--batch" in flags
    assert "--batch-interpreter" in flags
    assert "--no-interface" in flags
    assert "--quit" in flags


@pytest.mark.command_graph
def test_batch_build_args_defaults_exact_order() -> None:
    args = build_batch_args(["(gimp-quit 0)"])
    assert args == [
        "--new-instance",
        "--no-interface",
        "--console-messages",
        "--no-splash",
        "--batch",
        "(gimp-quit 0)",
        "--quit",
    ]


@pytest.mark.command_graph
def test_batch_build_args_with_interpreter_and_keep_alive() -> None:
    args = build_batch_args(
        ["pdb.gimp_quit(0)"],
        interpreter="python-fu-eval",
        quit_after=False,
    )
    assert "--batch-interpreter" in args
    idx = args.index("--batch-interpreter")
    assert args[idx + 1] == "python-fu-eval"
    assert "--quit" not in args


@pytest.mark.command_graph
def test_batch_build_args_disable_default_headless_flags() -> None:
    args = build_batch_args(
        ["(gimp-quit 0)"],
        new_instance=False,
        no_interface=False,
        console_messages=False,
        no_splash=False,
        quit_after=False,
    )
    assert "--new-instance" not in args
    assert "--no-interface" not in args
    assert "--console-messages" not in args
    assert "--no-splash" not in args
    assert "--quit" not in args
    assert args == ["--batch", "(gimp-quit 0)"]


@pytest.mark.command_graph
def test_batch_build_args_kitchen_sink() -> None:
    args = build_batch_args(
        ["(expr-1)", "(expr-2)"],
        interpreter="python-fu-eval",
        new_instance=True,
        no_interface=True,
        console_messages=True,
        no_splash=True,
        no_data=True,
        no_fonts=True,
        verbose=True,
        quit_after=True,
    )
    assert args == [
        "--new-instance",
        "--no-interface",
        "--console-messages",
        "--no-splash",
        "--no-data",
        "--no-fonts",
        "--verbose",
        "--batch-interpreter",
        "python-fu-eval",
        "--batch",
        "(expr-1)",
        "--batch",
        "(expr-2)",
        "--quit",
    ]


@pytest.mark.command_graph
def test_cli_info_version_wires_detect_version(runner: CliRunner) -> None:
    with patch("gimp_cli.info.detect_version", return_value="GNU Image Manipulation Program version 3.2.4"):
        result = runner.invoke(app, ["info", "version"])
    assert result.exit_code == 0
    assert "3.2.4" in result.output


@pytest.mark.command_graph
def test_cli_info_version_failure_bubbles_exit_code(runner: CliRunner) -> None:
    with patch("gimp_cli.info.detect_version", side_effect=typer.Exit(code=3)):
        result = runner.invoke(app, ["info", "version"])
    assert result.exit_code == 3


@pytest.mark.command_graph
def test_cli_batch_run_wires_run_command(runner: CliRunner) -> None:
    with patch("gimp_cli.batch.detect_version", return_value="GNU Image Manipulation Program version 3.2.4"), patch("gimp_cli.batch.run_command") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = ""
        result = runner.invoke(
            app,
            ["batch", "run", "--command", "(gimp-quit 0)", "--interpreter", "python-fu-eval"],
        )
    assert result.exit_code == 0
    called_args = run.call_args.args[0]
    assert "--batch-interpreter" in called_args
    assert "(gimp-quit 0)" in called_args


@pytest.mark.command_graph
def test_cli_batch_run_keep_alive_removes_quit(runner: CliRunner) -> None:
    with patch("gimp_cli.batch.detect_version", return_value="GNU Image Manipulation Program version 3.2.4"), patch("gimp_cli.batch.run_command") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = ""
        result = runner.invoke(
            app,
            ["batch", "run", "--command", "(gimp-quit 0)", "--keep-alive"],
        )
    assert result.exit_code == 0
    called_args = run.call_args.args[0]
    assert "--quit" not in called_args


@pytest.mark.command_graph
def test_cli_batch_run_nonzero_propagates_and_forwards_stderr(runner: CliRunner) -> None:
    with patch("gimp_cli.batch.detect_version", return_value="GNU Image Manipulation Program version 3.2.4"), patch("gimp_cli.batch.run_command") as run:
        run.return_value.returncode = 7
        run.return_value.stdout = ""
        run.return_value.stderr = "batch failed"
        result = runner.invoke(
            app,
            ["batch", "run", "--command", "(bad-expr)"],
        )
    assert result.exit_code == 7
    assert "batch failed" in result.output


@pytest.mark.command_graph
def test_cli_batch_run_preserves_expression_with_spaces(runner: CliRunner) -> None:
    expr = '(gimp-message "hello world with spaces")'
    with patch("gimp_cli.batch.detect_version", return_value="GNU Image Manipulation Program version 3.2.4"), patch("gimp_cli.batch.run_command") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = ""
        result = runner.invoke(app, ["batch", "run", "--command", expr])
    assert result.exit_code == 0
    called_args = run.call_args.args[0]
    idx = called_args.index("--batch")
    assert called_args[idx + 1] == expr


@pytest.mark.command_graph
def test_cli_batch_run_uses_batch_quit_expression_on_gimp2(runner: CliRunner) -> None:
    with patch("gimp_cli.batch.detect_version", return_value="GNU Image Manipulation Program version 2.10.36"), patch("gimp_cli.batch.run_command") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = ""
        result = runner.invoke(app, ["batch", "run", "--command", "(noop)"])
    assert result.exit_code == 0
    called_args = run.call_args.args[0]
    assert "--quit" not in called_args
    assert called_args[-2:] == ["--batch", "(gimp-quit 0)"]


@pytest.mark.command_graph
def test_pod_resize_expression_contains_scale_and_save() -> None:
    expr = build_resize_expression(
        input_path="in.png",
        output_path="out.png",
        width=4500,
        height=5400,
        interpolation="cubic",
        flatten=False,
    )
    assert "(gimp-file-load" in expr
    assert "(gimp-image-scale image 4500 5400)" in expr
    assert "(gimp-file-save" in expr
    assert "(gimp-image-flatten" not in expr


@pytest.mark.command_graph
def test_pod_fit_crop_expression_contains_crop_math() -> None:
    expr = build_fit_crop_expression(
        input_path="in.png",
        output_path="out.png",
        width=5400,
        height=4500,
        anchor="center",
        flatten=True,
    )
    assert "(gimp-image-crop image 5400 4500" in expr
    assert "(gimp-image-flatten image)" in expr
    assert "(gimp-file-save" in expr


@pytest.mark.command_graph
def test_pod_prep_expression_sets_print_resolution() -> None:
    expr = build_prep_expression(
        input_path="in.png",
        output_path="out.png",
        width=4500,
        height=5400,
        dpi=300,
        flatten=True,
    )
    assert "(gimp-image-scale image 4500 5400)" in expr
    assert "(gimp-image-set-resolution image 300 300)" in expr
    assert "(gimp-image-flatten image)" in expr


@pytest.mark.command_graph
def test_pod_batch_args_kitchen_sink() -> None:
    args = build_pod_batch_args(
        expression="(noop)",
        no_data=True,
        no_fonts=True,
        verbose=True,
        keep_alive=False,
        gimp_version_text="GNU Image Manipulation Program version 3.2.4",
    )
    assert args == [
        "--new-instance",
        "--no-interface",
        "--console-messages",
        "--no-splash",
        "--no-data",
        "--no-fonts",
        "--verbose",
        "--batch",
        "(noop)",
        "--quit",
    ]


@pytest.mark.command_graph
def test_cli_pod_resize_wires_run_command(runner: CliRunner) -> None:
    with patch("gimp_cli.pod.detect_version", return_value="GNU Image Manipulation Program version 3.2.4"), patch("gimp_cli.pod.run_command") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = ""
        result = runner.invoke(
            app,
            [
                "pod",
                "resize",
                "--input",
                "in.png",
                "--output",
                "out.png",
                "--width",
                "4500",
                "--height",
                "5400",
            ],
        )
    assert result.exit_code == 0
    called_args = run.call_args.args[0]
    assert "--batch" in called_args
    assert "--quit" in called_args
