"""Logic for finetune train command — build training arguments."""

from ..backend import base_model_name_from_size


def build_train_args(
    *,
    dataset: str,
    output_dir: str,
    base_model: str = "1.7b",
    epochs: int | None = None,
    batch_size: int | None = None,
    learning_rate: float | None = None,
    speaker_name: str = "custom_speaker",
) -> list[str]:
    """Build argument list for the fine-tuning script.

    Returns args for `python sft_12hz.py <args>`.
    """
    model_name = base_model_name_from_size(base_model)
    args = [
        "--init_model_path", model_name,
        "--output_model_path", output_dir,
        "--train_jsonl", dataset,
        "--speaker_name", speaker_name,
    ]

    if epochs is not None:
        args.extend(["--num_epochs", str(epochs)])
    if batch_size is not None:
        args.extend(["--batch_size", str(batch_size)])
    if learning_rate is not None:
        args.extend(["--lr", str(learning_rate)])

    return args
