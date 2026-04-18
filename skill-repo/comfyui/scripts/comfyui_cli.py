"""Entry point for uv run comfyui_cli.py"""
import sys
from comfyui_cli import app
from comfyui_cli.backend import ComfyError, print_error_and_exit


def main() -> None:
    try:
        app()
    except NotImplementedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("This command is scaffolded but not yet implemented.", file=sys.stderr)
        sys.exit(1)
    except ComfyError as exc:
        print_error_and_exit(exc)


if __name__ == "__main__":
    main()
