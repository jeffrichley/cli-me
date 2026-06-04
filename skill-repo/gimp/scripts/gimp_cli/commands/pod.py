"""Print-on-demand convenience command logic."""

from __future__ import annotations

from gimp_cli.commands.batch import build_batch_args


def _scheme_path(value: str) -> str:
    return value.replace("\\", "/").replace('"', '\\"')


def _interpolation_symbol(interpolation: str) -> str:
    mapping = {
        "none": "INTERPOLATION-NONE",
        "linear": "INTERPOLATION-LINEAR",
        "cubic": "INTERPOLATION-CUBIC",
        "lanczos": "INTERPOLATION-LANCZOS",
    }
    return mapping[interpolation]


def build_resize_expression(
    *,
    input_path: str,
    output_path: str,
    width: int,
    height: int,
    interpolation: str,
    flatten: bool,
) -> str:
    flatten_stmt = "(set! drawable (car (gimp-image-flatten image)))" if flatten else ""
    return (
        f'(let* ((image (car (gimp-file-load RUN-NONINTERACTIVE "{_scheme_path(input_path)}" "{_scheme_path(input_path)}"))) '
        f"(drawable (car (gimp-image-get-active-layer image)))) "
        f"(gimp-context-set-interpolation {_interpolation_symbol(interpolation)}) "
        f"(gimp-image-scale image {width} {height}) "
        f"{flatten_stmt} "
        f'(gimp-file-save RUN-NONINTERACTIVE image drawable "{_scheme_path(output_path)}" "{_scheme_path(output_path)}") '
        f"(gimp-image-delete image))"
    )


def build_fit_crop_expression(
    *,
    input_path: str,
    output_path: str,
    width: int,
    height: int,
    anchor: str,
    flatten: bool,
) -> str:
    x_offset = "(if (> target-ratio source-ratio) (/ (- new-w target-w) 2) 0)"
    y_offset = "(if (> source-ratio target-ratio) (/ (- new-h target-h) 2) 0)"
    if anchor == "top":
        y_offset = "0"
    elif anchor == "bottom":
        y_offset = "(if (> source-ratio target-ratio) (- new-h target-h) 0)"
    elif anchor == "left":
        x_offset = "0"
    elif anchor == "right":
        x_offset = "(if (> target-ratio source-ratio) (- new-w target-w) 0)"
    flatten_stmt = "(set! drawable (car (gimp-image-flatten image)))" if flatten else ""
    return (
        f'(let* ((image (car (gimp-file-load RUN-NONINTERACTIVE "{_scheme_path(input_path)}" "{_scheme_path(input_path)}"))) '
        f"(drawable (car (gimp-image-get-active-layer image))) "
        f"(source-w (car (gimp-image-width image))) (source-h (car (gimp-image-height image))) "
        f"(target-w {width}) (target-h {height}) "
        f"(source-ratio (/ source-w source-h)) (target-ratio (/ target-w target-h)) "
        f"(new-w (if (> target-ratio source-ratio) target-w (* source-w (/ target-h source-h)))) "
        f"(new-h (if (> source-ratio target-ratio) target-h (* source-h (/ target-w source-w))))) "
        f"(gimp-context-set-interpolation INTERPOLATION-CUBIC) "
        f"(gimp-image-scale image (inexact->exact (round new-w)) (inexact->exact (round new-h))) "
        f"(gimp-image-crop image {width} {height} (inexact->exact (round {x_offset})) (inexact->exact (round {y_offset}))) "
        f"{flatten_stmt} "
        f'(gimp-file-save RUN-NONINTERACTIVE image drawable "{_scheme_path(output_path)}" "{_scheme_path(output_path)}") '
        f"(gimp-image-delete image))"
    )


def build_prep_expression(
    *,
    input_path: str,
    output_path: str,
    width: int,
    height: int,
    dpi: int,
    flatten: bool,
) -> str:
    flatten_stmt = "(set! drawable (car (gimp-image-flatten image)))" if flatten else ""
    return (
        f'(let* ((image (car (gimp-file-load RUN-NONINTERACTIVE "{_scheme_path(input_path)}" "{_scheme_path(input_path)}"))) '
        f"(drawable (car (gimp-image-get-active-layer image)))) "
        f"(gimp-context-set-interpolation INTERPOLATION-CUBIC) "
        f"(gimp-image-scale image {width} {height}) "
        f"(gimp-image-set-resolution image {dpi} {dpi}) "
        f"{flatten_stmt} "
        f'(gimp-file-save RUN-NONINTERACTIVE image drawable "{_scheme_path(output_path)}" "{_scheme_path(output_path)}") '
        f"(gimp-image-delete image))"
    )


def build_pod_batch_args(
    *,
    expression: str,
    no_data: bool,
    no_fonts: bool,
    verbose: bool,
    keep_alive: bool,
    gimp_version_text: str,
) -> list[str]:
    quit_via_flag = "version 2." not in gimp_version_text.lower()
    return build_batch_args(
        [expression],
        no_data=no_data,
        no_fonts=no_fonts,
        verbose=verbose,
        quit_after=not keep_alive,
        quit_via_flag=quit_via_flag,
    )
