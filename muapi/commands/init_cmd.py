"""muapi init — create a muapi.json project config in the current directory."""
import json
from pathlib import Path

import typer

from ..utils import console, error_exit

_PROJECT_FILE = "muapi.json"
_SCHEMA_URL = "https://muapi.ai/schema/cli.json"

_DEFAULT_CONFIG = {
    "$schema": _SCHEMA_URL,
    "defaultModel": "flux-dev-image",
    "outputDir": "muapi-output",
    "aliases": {},
}


def init(
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip prompts and write defaults"),
    force: bool = typer.Option(False, "-f", "--force", help="Overwrite an existing muapi.json"),
):
    """Create a muapi.json project config with a defaultModel and alias stubs.

    \b
    Examples:
      muapi init            # interactive
      muapi init -y         # write defaults silently
      muapi init -y -f      # overwrite existing
    """
    target = Path.cwd() / _PROJECT_FILE

    if target.exists() and not force:
        error_exit(
            f"{_PROJECT_FILE} already exists. Use --force to overwrite.",
        )

    config = dict(_DEFAULT_CONFIG)

    if not yes:
        from rich.prompt import Prompt
        default_model = Prompt.ask(
            "Default model",
            default=config["defaultModel"],
            console=console,
        )
        output_dir = Prompt.ask(
            "Output directory",
            default=config["outputDir"],
            console=console,
        )
        config["defaultModel"] = default_model
        config["outputDir"] = output_dir

    target.write_text(json.dumps(config, indent=2) + "\n")
    console.print(f"[green]Wrote {_PROJECT_FILE}[/green]")
    console.print()
    console.print("Now try:")
    console.print(f"  [cyan]muapi run -p \"a serene mountain lake at sunrise\"[/cyan]")
    console.print(f"  Add aliases by editing [bold]{_PROJECT_FILE}[/bold]")
    console.print()
