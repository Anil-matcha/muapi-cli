"""Shared output, display, and download helpers — agent-friendly."""
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import exitcodes

# ── Colour / NO_COLOR support ─────────────────────────────────────────────────
# Honour the NO_COLOR env var (https://no-color.org/) and --no-color flag.
# Both CI environments and agent pipelines typically set NO_COLOR=1.
_NO_COLOR = bool(os.environ.get("NO_COLOR") or os.environ.get("MUAPI_NO_COLOR"))

console = Console(stderr=True, no_color=_NO_COLOR)   # status/progress → stderr
out     = Console(no_color=_NO_COLOR)                 # actual output   → stdout


def disable_color() -> None:
    """Called when user passes --no-color flag."""
    global console, out, _NO_COLOR
    _NO_COLOR = True
    console = Console(stderr=True, no_color=True)
    out     = Console(no_color=True)


# ── jq-style filtering ────────────────────────────────────────────────────────

def apply_jq(data: Any, expression: str) -> Any:
    """Apply a simple jq-style expression to data.

    Supports:
      .key            → dict field
      .key.nested     → nested dict fields
      .[0]            → list index
      .[]             → all list items (returns list)
      .key[]          → field then list
      .key[0]         → field then index
    """
    if not expression or expression == ".":
        return data
    # Strip leading dot
    expr = expression.lstrip(".")
    if not expr:
        return data
    return _jq_walk(data, expr)


def _jq_walk(data: Any, expr: str) -> Any:
    if not expr:
        return data
    # Array index: [N]
    if expr.startswith("["):
        end = expr.index("]")
        idx_str = expr[1:end]
        rest = expr[end + 1:].lstrip(".")
        if idx_str == "":
            # .[] — all items
            if not isinstance(data, list):
                raise ValueError(f"Expected list for '[]', got {type(data).__name__}")
            return [_jq_walk(item, rest) for item in data]
        else:
            idx = int(idx_str)
            if not isinstance(data, list):
                raise ValueError(f"Expected list for '[{idx}]', got {type(data).__name__}")
            return _jq_walk(data[idx], rest)
    # Key access
    if "." in expr:
        key, rest = expr.split(".", 1)
        # Handle key[] inline
        if key.endswith("[]"):
            key = key[:-2]
            val = data[key]
            return [_jq_walk(item, rest) if rest else item for item in val]
        if key.endswith("]"):
            bracket = key.index("[")
            idx = int(key[bracket + 1:-1])
            key = key[:bracket]
            return _jq_walk(data[key][idx], rest)
        return _jq_walk(data[key], rest)
    else:
        key = expr
        if key.endswith("[]"):
            return data[key[:-2]]
        if key.endswith("]"):
            bracket = key.index("[")
            idx = int(key[bracket + 1:-1])
            return data[key[:bracket]][idx]
        return data[key]


# ── JSON output ───────────────────────────────────────────────────────────────

def print_json(data: Any, jq: Optional[str] = None) -> None:
    if jq:
        try:
            data = apply_jq(data, jq)
        except Exception as e:
            error_exit(f"jq filter error: {e}", exitcodes.VALIDATION)
    if isinstance(data, (dict, list)):
        out.print_json(json.dumps(data))
    else:
        out.print(json.dumps(data))


def print_result(
    result: dict,
    output_json: bool,
    label: str = "Result",
    jq: Optional[str] = None,
) -> None:
    if output_json or jq:
        print_json(result, jq)
        return
    status  = result.get("status", "")
    outputs = result.get("outputs", [])

    lines = []
    if status:
        color = "green" if status == "completed" else ("red" if status == "failed" else "yellow")
        lines.append(f"[bold]Status:[/bold] [{color}]{status}[/{color}]")
    if req_id := result.get("request_id"):
        lines.append(f"[bold]Request ID:[/bold] {req_id}")
    if outputs:
        lines.append("[bold]Outputs:[/bold]")
        for o in outputs:
            lines.append(f"  [cyan]{o}[/cyan]")

    if lines:
        out.print(Panel("\n".join(lines), title=f"[bold magenta]{label}[/bold magenta]"))
    else:
        out.print_json(json.dumps(result))


# ── Download ──────────────────────────────────────────────────────────────────

def download_outputs(result: dict, dest: str) -> None:
    outputs = result.get("outputs", [])
    if not outputs:
        console.print("[yellow]No outputs to download.[/yellow]")
        return
    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(outputs):
        filename = _filename_from_url(url, i)
        target   = dest_path / filename
        console.print(f"Downloading [cyan]{url}[/cyan] → [green]{target}[/green]")
        with httpx.stream("GET", url, follow_redirects=True) as r:
            with open(target, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        console.print(f"  [green]Saved[/green] {target}")


def _filename_from_url(url: str, index: int) -> str:
    path = urlparse(url).path
    name = path.split("/")[-1]
    if not name or "." not in name:
        name = f"output_{index}"
    return name


# ── Errors ────────────────────────────────────────────────────────────────────

def error_exit(msg: str, code: int = exitcodes.ERROR) -> None:
    """Print error to stderr and exit with a semantic exit code."""
    console.print(f"[bold red]Error:[/bold red] {msg}")
    sys.exit(code)


# ── Spinner ───────────────────────────────────────────────────────────────────

def spinner_status(msg: str):
    return console.status(f"[bold cyan]{msg}[/bold cyan]", spinner="dots")


# ── Dry-run display ───────────────────────────────────────────────────────────

def print_dry_run(endpoint: str, payload: dict) -> None:
    """Show what request would be sent without executing it."""
    from .config import BASE_URL
    out.print(Panel(
        f"[bold]Method:[/bold] POST\n"
        f"[bold]URL:[/bold]    {BASE_URL}/{endpoint.lstrip('/')}\n"
        f"[bold]Payload:[/bold]\n{json.dumps(payload, indent=2)}",
        title="[bold yellow]Dry Run — no request sent[/bold yellow]",
    ))


# ── Stdin helper ──────────────────────────────────────────────────────────────

def read_stdin_if_dash(value: Optional[str]) -> Optional[str]:
    """If value is '-', read a line from stdin. Useful for piping prompts."""
    if value == "-":
        return sys.stdin.readline().strip()
    return value
