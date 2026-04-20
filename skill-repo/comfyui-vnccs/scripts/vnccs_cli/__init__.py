"""Agent-native CLI for the ComfyUI_VNCCS visual novel character pipeline."""

import typer

from vnccs_cli.check import app as check_app
from vnccs_cli.character import app as character_app
from vnccs_cli.clothing import app as clothing_app
from vnccs_cli.emotion import app as emotion_app
from vnccs_cli.sprite import app as sprite_app
from vnccs_cli.dataset import app as dataset_app
from vnccs_cli.pose import app as pose_app
from vnccs_cli.config import app as config_app

app = typer.Typer(
    name="vnccs-cli",
    help="Agent-native CLI for ComfyUI_VNCCS — character sheets, clothing, emotions, sprites.",
    no_args_is_help=True,
)

app.add_typer(check_app, name="check")
app.add_typer(character_app, name="character")
app.add_typer(clothing_app, name="clothing")
app.add_typer(emotion_app, name="emotion")
app.add_typer(sprite_app, name="sprite")
app.add_typer(dataset_app, name="dataset")
app.add_typer(pose_app, name="pose")
app.add_typer(config_app, name="config")
