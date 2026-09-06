"""muapi keys — list, create, and delete API keys."""
import json

import httpx
import typer

from .. import exitcodes
from ..config import BASE_URL, get_api_key
from ..utils import console, error_exit, out

app = typer.Typer(help="Manage API keys for your muapi.ai account.")


def _headers() -> dict:
    key = get_api_key()
    if not key:
        error_exit("No API key configured. Run: muapi auth configure", exitcodes.AUTH_ERROR)
    return {"x-api-key": key}


@app.command("list")
def list_keys(
    output_json: bool = typer.Option(False, "--output-json", "-j", help="Print raw JSON"),
):
    """List all API keys on your account."""
    try:
        resp = httpx.get(f"{BASE_URL}/keys", headers=_headers(), timeout=30.0)
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code in (401, 403):
        error_exit("Authentication failed. Run: muapi auth configure", exitcodes.AUTH_ERROR)
    if resp.status_code >= 400:
        error_exit(f"Request failed: {resp.text}", exitcodes.ERROR)

    keys = resp.json()
    if output_json:
        out.print_json(json.dumps(keys))
        return

    if not keys:
        console.print("No API keys found.")
        return

    from rich.table import Table
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Active")
    table.add_column("Created")
    table.add_column("Last Used")
    for k in keys:
        table.add_row(
            str(k["id"]),
            k["name"],
            "[green]yes[/green]" if k["is_active"] else "[red]no[/red]",
            (k.get("created_at") or "")[:10],
            (k.get("last_used_at") or "never")[:10],
        )
    console.print(table)


@app.command("create")
def create_key(
    name: str = typer.Option("cli", "--name", "-n", help="Label for this key"),
    output_json: bool = typer.Option(False, "--output-json", "-j", help="Print raw JSON"),
):
    """Create a new API key (shown once — save it immediately)."""
    try:
        resp = httpx.post(
            f"{BASE_URL}/keys",
            json={"name": name},
            headers=_headers(),
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code in (401, 403):
        error_exit("Authentication failed. Run: muapi auth configure", exitcodes.AUTH_ERROR)
    if resp.status_code >= 400:
        error_exit(f"Request failed: {resp.text}", exitcodes.ERROR)

    data = resp.json()
    if output_json:
        out.print_json(json.dumps(data))
        return

    console.print(f"[bold green]API key created (ID {data['id']}):[/bold green]")
    console.print(f"[bold yellow]{data['api_key']}[/bold yellow]")
    console.print("[dim]Save it now — it won't be shown again.[/dim]")


@app.command("delete")
def delete_key(
    key_id: int = typer.Argument(..., help="ID of the key to delete (from 'muapi keys list')"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete an API key by ID."""
    if not yes:
        typer.confirm(f"Delete API key ID {key_id}?", abort=True)

    try:
        resp = httpx.delete(f"{BASE_URL}/keys/{key_id}", headers=_headers(), timeout=30.0)
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code == 404:
        error_exit(f"API key {key_id} not found.", exitcodes.NOT_FOUND)
    if resp.status_code in (401, 403):
        error_exit("Authentication failed.", exitcodes.AUTH_ERROR)
    if resp.status_code >= 400:
        error_exit(f"Request failed: {resp.text}", exitcodes.ERROR)

    console.print(f"[green]API key {key_id} deleted.[/green]")
