"""Agent-native CLI for ComfyUI."""

import typer

from comfyui_cli.server import app as server_app
from comfyui_cli.queue_cmd import app as queue_app
from comfyui_cli.workflow import app as workflow_app
from comfyui_cli.model import app as model_app
from comfyui_cli.assets_input import app as input_app
from comfyui_cli.assets_output import app as output_app
from comfyui_cli.custom_nodes import app as custom_nodes_app

app = typer.Typer(
    name="comfyui-cli",
    help="Agent-native CLI for ComfyUI — submit workflows, track progress, manage assets.",
    no_args_is_help=True,
)

app.add_typer(server_app, name="server")
app.add_typer(queue_app, name="queue")
app.add_typer(workflow_app, name="workflow")
app.add_typer(model_app, name="model")
app.add_typer(input_app, name="input")
app.add_typer(output_app, name="output")
app.add_typer(custom_nodes_app, name="custom-nodes")
