"""Backend helpers: pipeline loading, device detection, token handling."""

from __future__ import annotations

import os
import sys
from functools import lru_cache

import typer


def get_token(token: str | None = None) -> str:
    """Get HuggingFace token from argument, environment, or local cache."""
    if token:
        return token
    env_token = os.environ.get("HF_TOKEN")
    if env_token:
        return env_token
    # Check huggingface_hub's saved token (from `huggingface-cli login`)
    try:
        from huggingface_hub import get_token as hf_get_token

        saved = hf_get_token()
        if saved:
            return saved
    except Exception:
        pass
    typer.echo(
        "ERROR: HuggingFace token required. Set HF_TOKEN environment variable, "
        "run `huggingface-cli login`, or pass --token.",
        err=True,
    )
    raise typer.Exit(code=1)


def get_device(device: str = "auto") -> str:
    """Resolve device string to a torch device name."""
    if device != "auto":
        return device
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_pipeline(name: str, token: str | None = None, device: str = "auto"):
    """Load a pyannote pipeline from HuggingFace."""
    import torch
    from pyannote.audio import Pipeline

    resolved_token = get_token(token)
    resolved_device = get_device(device)

    pipeline = Pipeline.from_pretrained(name, token=resolved_token)
    pipeline.to(torch.device(resolved_device))
    return pipeline


def load_inference(
    model_name: str, token: str | None = None, device: str = "auto", **kwargs
):
    """Load a pyannote model and create an Inference object."""
    import torch
    from pyannote.audio import Inference, Model

    resolved_token = get_token(token)
    resolved_device = get_device(device)

    model = Model.from_pretrained(model_name, token=resolved_token)
    model.to(torch.device(resolved_device))
    return Inference(model, device=torch.device(resolved_device), **kwargs)
