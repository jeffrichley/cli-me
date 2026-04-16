"""Logic for info device command."""

import json

import torch


def get_device_info() -> dict:
    """Return device information as a dict."""
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        return {
            "device": "cuda",
            "gpu_name": torch.cuda.get_device_name(0),
            "vram_gb": round(props.total_memory / 1024**3, 1),
        }
    if torch.backends.mps.is_available():
        return {
            "device": "mps",
            "gpu_name": "Apple Silicon",
            "vram_gb": None,
        }
    return {
        "device": "cpu",
        "gpu_name": None,
        "vram_gb": None,
    }


def format_device_info(info: dict, pretty: bool = False) -> str:
    """Format device info as JSON or human-readable."""
    if pretty:
        lines = [f"Device: {info['device']}"]
        if info["gpu_name"]:
            lines.append(f"GPU: {info['gpu_name']}")
        if info["vram_gb"]:
            lines.append(f"VRAM: {info['vram_gb']} GB")
        return "\n".join(lines)
    return json.dumps(info, indent=2)
