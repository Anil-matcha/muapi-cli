"""muapi docs — access the muapi.ai API documentation."""
import json
import webbrowser

import httpx
import typer

from .. import exitcodes
from ..config import BASE_URL
from ..utils import console, error_exit, out

app = typer.Typer(help="Access the muapi.ai API documentation.")

_HOST = BASE_URL.replace("/api/v1", "")
_OPENAPI_URL = f"{_HOST}/openapi.json"
_DOCS_URL = f"{_HOST}/docs"
_REDOC_URL = f"{_HOST}/redoc"


@app.command("openapi")
def openapi(
    output_json: bool = typer.Option(True, "--output-json/--no-output-json", "-j",
                                      help="Print the raw OpenAPI JSON (default: on)"),
    jq: str = typer.Option("", "--jq", help="jq-style filter (e.g. '.paths | keys[]')"),
    save: str = typer.Option("", "--save", "-s", help="Save spec to a file path"),
):
    """Fetch and print the muapi.ai OpenAPI spec.

    Useful for agents to discover all available endpoints, request schemas,
    and response shapes without reading source code.

    Examples:

    \\b
    muapi docs openapi --jq '.paths | keys[]'
    muapi docs openapi --save ./muapi-openapi.json
    """
    try:
        resp = httpx.get(_OPENAPI_URL, timeout=30.0)
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code >= 400:
        error_exit(f"Failed to fetch OpenAPI spec: {resp.status_code}", exitcodes.ERROR)

    spec = resp.json()

    if save:
        import pathlib
        pathlib.Path(save).write_text(json.dumps(spec, indent=2))
        console.print(f"[green]Saved to {save}[/green]")
        return

    if jq:
        from ..utils import apply_jq
        filtered = apply_jq(spec, jq)
        if isinstance(filtered, (dict, list)):
            out.print_json(json.dumps(filtered, indent=2))
        else:
            out.print(str(filtered))
        return

    if output_json:
        out.print_json(json.dumps(spec))
    else:
        # Human summary
        info = spec.get("info", {})
        paths = spec.get("paths", {})
        console.print(f"[bold]{info.get('title', 'muapi')}[/bold] v{info.get('version', '?')}")
        console.print(f"{len(paths)} endpoints — full spec at: [blue]{_OPENAPI_URL}[/blue]")
        console.print(f"Interactive docs: [blue]{_DOCS_URL}[/blue]")


@app.command("open")
def open_docs(
    ui: str = typer.Option("swagger", "--ui", help="UI to open: swagger, redoc"),
):
    """Open the API documentation in your browser."""
    url = _REDOC_URL if ui == "redoc" else _DOCS_URL
    console.print(f"Opening [blue]{url}[/blue]")
    webbrowser.open(url)
