"""muapi CLI — official command-line interface for muapi.ai"""
from typing import Optional

import typer
from rich import print as rprint

from . import __version__
from .commands import auth, account, audio, config_cmd, docs, edit, enhance, image, init_cmd, keys, models, open_cmd, predict, run, upload, video, workflow
from .commands import mcp_server
from .dynamic_help import maybe_handle_run_help

app = typer.Typer(
    name="muapi",
    help="muapi.ai CLI — generate images, videos, and audio from the terminal.",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# ── Subcommand groups ──────────────────────────────────────────────────────────

app.add_typer(auth.app,        name="auth",    help="Log in, register, or configure API key.")
app.add_typer(account.app,     name="account", help="Check balance and top up credits.")
app.add_typer(keys.app,        name="keys",    help="List, create, and delete API keys.")
app.add_typer(image.app,       name="image",   help="Generate or edit images.")
app.add_typer(video.app,       name="video",   help="Generate videos from text or images.")
app.add_typer(audio.app,       name="audio",   help="Create or remix music and audio.")
app.add_typer(enhance.app,     name="enhance", help="Enhance images (upscale, bg-remove, face-swap…).")
app.add_typer(edit.app,        name="edit",    help="Edit videos (effects, lipsync, dance, dress…).")
app.add_typer(predict.app,     name="predict", help="Check or wait for async prediction results.")

# `run` is a single top-level command, not a group, so its positional MODEL
# argument doesn't collide with subcommand routing.
app.command(
    "run",
    help="Run any model by endpoint name (schema-driven; try `muapi run <model> -h`).",
    context_settings={"help_option_names": ["-h", "--help"]},
)(run.run)
app.add_typer(upload.app,      name="upload",  help="Upload local files to get a hosted URL.")
app.add_typer(models.app,      name="models",  help="Discover all available models.")
app.add_typer(workflow.app,    name="workflow", help="Build, run, and visualize multi-step AI workflows.")
app.add_typer(config_cmd.app,  name="config",  help="Get and set persistent CLI configuration.")
app.add_typer(docs.app,        name="docs",    help="Access the muapi.ai API documentation.")
app.add_typer(mcp_server.app,  name="mcp",     help="Run as an MCP server for AI agent integration.")

app.command(
    "init",
    help="Create a muapi.json project config with defaultModel and alias stubs.",
    context_settings={"help_option_names": ["-h", "--help"]},
)(init_cmd.init)

app.command(
    "open",
    help="Open a muapi.ai page in your browser (dashboard, models, docs, access-keys…).",
    context_settings={"help_option_names": ["-h", "--help"]},
)(open_cmd.open_page)


@app.command("version")
def version(
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Show the muapi CLI version."""
    if output_json:
        import json
        from .utils import out
        out.print_json(json.dumps({"version": __version__, "name": "muapi-cli"}))
    else:
        rprint(f"muapi CLI [bold]{__version__}[/bold]")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    no_color: bool = typer.Option(
        False, "--no-color",
        help="Disable colored output (also respects NO_COLOR env var)",
        is_eager=True,
    ),
    version_flag: bool = typer.Option(
        False, "--version", "-V",
        help="Show version and exit",
        is_eager=True,
    ),
):
    if no_color:
        from .utils import disable_color
        disable_color()

    if version_flag:
        rprint(f"muapi CLI [bold]{__version__}[/bold]")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        rprint(ctx.get_help())


def _entrypoint() -> None:
    # Intercept `muapi run <model> -h` so we can print model-specific
    # input help from the live OpenAPI schema. Falls through to Typer
    # on any failure (network down, unknown model, missing schema).
    import sys
    if maybe_handle_run_help(sys.argv[1:]):
        return
    app()


if __name__ == "__main__":
    _entrypoint()
