"""Finetune command group — custom voice model training pipeline."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import save_audio, detect_device
from .commands import finetune_prepare, finetune_train, finetune_generate

finetune_app = typer.Typer(help="Fine-tune custom voice models.", no_args_is_help=True)
app.add_typer(finetune_app, name="finetune")


@finetune_app.command()
def prepare(
    audio_dir: Annotated[str, typer.Option("--audio-dir", help="Directory of WAV files")],
    output_dir: Annotated[str, typer.Option("--output-dir", help="Where to write prepared dataset")],
    lang: Annotated[str, typer.Option(help="Language of the audio")] = "en",
) -> None:
    """Prepare training data from audio files."""
    import json

    try:
        result = finetune_prepare.validate_audio_dir(audio_dir)
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    if not result["valid"]:
        typer.echo(f"ERROR: No WAV files found in {audio_dir}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Found {result['wav_count']} WAV files in {audio_dir}")
    typer.echo(json.dumps(result, indent=2))
    typer.echo(f"\nDataset preparation would write to: {output_dir}")
    typer.echo("NOTE: Full dataset preparation requires the Qwen3-TTS finetuning scripts.")


@finetune_app.command()
def train(
    dataset: Annotated[str, typer.Option("--dataset", help="Path to prepared training JSONL")],
    output_dir: Annotated[str, typer.Option("--output-dir", help="Where to save trained model")],
    base_model: Annotated[str, typer.Option("--base-model", help="Base model size (1.7b or 0.6b)")] = "1.7b",
    epochs: Annotated[Optional[int], typer.Option(help="Number of training epochs")] = None,
    batch_size: Annotated[Optional[int], typer.Option(help="Training batch size")] = None,
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu)")] = None,
) -> None:
    """Train a custom voice model."""
    try:
        args = finetune_train.build_train_args(
            dataset=dataset,
            output_dir=output_dir,
            base_model=base_model,
            epochs=epochs,
            batch_size=batch_size,
        )
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Training args: {' '.join(args)}")
    typer.echo("NOTE: Run the actual training via the Qwen3-TTS finetuning scripts.")


@finetune_app.command("generate")
def generate_cmd(
    content: Annotated[str, typer.Argument(help="Text to synthesize")],
    model_dir: Annotated[str, typer.Option("--model-dir", help="Path to fine-tuned model directory")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")],
    instruct: Annotated[Optional[str], typer.Option(help="Style/emotion instruction")] = None,
    lang: Annotated[str, typer.Option(help="Language")] = "Auto",
    format: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "wav",
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """Generate speech using a fine-tuned model."""
    import torch
    from qwen_tts import Qwen3TTSModel

    dev = detect_device(device)
    dtype = torch.bfloat16 if dev != "cpu" else torch.float32
    model = Qwen3TTSModel.from_pretrained(
        model_dir,
        device_map=f"{dev}:0" if dev == "cuda" else dev,
        dtype=dtype,
    )
    try:
        audio, sr = finetune_generate.generate_from_finetuned(
            model,
            text=content,
            language=lang,
            instruct=instruct,
        )
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)
    path = save_audio(audio, sr, output, format=format)
    typer.echo(f"Saved to {path}")
