"""muapi upload — upload local files to get a hosted URL."""
from pathlib import Path

import typer

from .. import client
from ..utils import error_exit, print_result, console

app = typer.Typer(help="Upload local files to get a hosted URL for use in generation.")


@app.command("file")
def upload_file(
    file_path: str = typer.Argument(..., help="Local file path to upload"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Upload a local file and get back a hosted URL."""
    path = Path(file_path)
    if not path.exists():
        error_exit(f"File not found: {file_path}")
    try:
        console.print(f"Uploading [cyan]{file_path}[/cyan]...")
        result = client.upload_file(str(path))
    except client.MuapiError as e:
        error_exit(str(e))

    print_result(result, output_json, label="Upload")
    if not output_json:
        url = result.get("url") or result.get("file_url") or result.get("output", [None])[0] if isinstance(result.get("output"), list) else result.get("output")
        if url:
            console.print(f"\nHosted URL: [bold green]{url}[/bold green]")
