"""muapi config — get and set persistent CLI settings."""
import json

import typer

from ..config import get_all_settings, get_setting, set_setting, _CONFIG_FILE
from ..utils import console, out

app = typer.Typer(help="Manage CLI configuration (default model, output format, etc.).")

_KNOWN_KEYS = {
    "output":        "Default output format: 'human' or 'json'",
    "model.image":   "Default image generation model (e.g. flux-dev)",
    "model.video":   "Default video generation model (e.g. kling-master)",
    "model.audio":   "Default audio model (e.g. suno-create-music)",
    "no_color":      "Disable colored output: 'true' or 'false'",
    "poll_interval": "Seconds between result polls (default 3)",
    "timeout":       "Max seconds to wait for results (default 600)",
}


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Setting key (e.g. output, model.image)"),
    value: str = typer.Argument(..., help="Value to assign"),
):
    """Set a persistent CLI configuration value.

    Examples:

    \\b
    muapi config set output json
    muapi config set model.image flux-schnell
    muapi config set no_color true
    """
    set_setting(key, value)
    console.print(f"[green]Set [bold]{key}[/bold] = {value}[/green]")


@app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Setting key to read"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Get the current value of a configuration key."""
    value = get_setting(key)
    if value is None:
        console.print(f"[dim]{key} is not set[/dim]")
        raise typer.Exit(0)
    if output_json:
        out.print_json(json.dumps({key: value}))
    else:
        console.print(f"[bold]{key}[/bold] = {value}")


@app.command("list")
def config_list(
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Show all configured settings."""
    settings = get_all_settings()
    if output_json:
        out.print_json(json.dumps(settings))
        return

    if not settings:
        console.print(f"[dim]No settings configured. Config file: {_CONFIG_FILE}[/dim]")
        console.print("\nAvailable keys:")
        for k, desc in _KNOWN_KEYS.items():
            console.print(f"  [bold]{k}[/bold]  — {desc}")
        return

    from rich.table import Table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Key")
    table.add_column("Value")
    for k, v in settings.items():
        table.add_row(k, str(v))
    console.print(table)
    console.print(f"\n[dim]Config file: {_CONFIG_FILE}[/dim]")
