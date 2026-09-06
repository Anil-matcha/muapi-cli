"""Dynamic per-model `--help` for `muapi run <model>`.

Typer's static help only knows about flags that are *declared* on a command,
so it can't show per-model inputs. We sniff argv before Typer runs, and if
the user is asking for help on `muapi run <model>`, we fetch the model's
OpenAPI schema and print its real properties.

If anything goes wrong (network, unknown model, malformed spec), we return
False so the caller falls through to Typer's normal static help.
"""
from __future__ import annotations

import sys
from typing import Optional

from rich.console import Console
from rich.table import Table

from . import schema_introspect


_HELP_FLAGS = {"-h", "--help"}


def detect_run_help(argv: list[str]) -> Optional[str]:
    """Return the model token if argv looks like `muapi run <model> -h`.

    The check is intentionally permissive — extra flags between `run`
    and `-h` don't disqualify (e.g. `run flux-dev -p foo -h`).
    """
    try:
        run_idx = argv.index("run")
    except ValueError:
        return None
    rest = argv[run_idx + 1:]
    if not rest:
        return None
    if not any(flag in rest for flag in _HELP_FLAGS):
        return None
    # First non-flag token after `run` is the model.
    for token in rest:
        if token in _HELP_FLAGS:
            return None  # asked for help with no model
        if not token.startswith("-"):
            return token
    return None


def print_dynamic_help(model: str) -> bool:
    """Print schema-driven help for `model`. Returns True on success."""
    # Resolve aliases the same way the run command does.
    try:
        from .commands.run import resolve_model
        endpoint = resolve_model(model)
    except Exception:
        endpoint = model

    try:
        described = schema_introspect.lookup(endpoint)
    except Exception:
        return False
    if not described:
        return False

    console = Console(stderr=False)
    console.print()
    console.print(f"[bold magenta]muapi run {model}[/bold magenta]")
    if endpoint != model:
        console.print(f"  [dim]endpoint:[/dim] {endpoint}")
    if described["title"] and described["title"] != endpoint:
        console.print(f"  [dim]schema:  [/dim] {described['title']}")
    console.print()
    console.print("[bold]Usage:[/bold] muapi run "
                  f"{model} [-p PROMPT] [-i KEY=VALUE ...] [--input-file FILE] [global opts]")
    console.print()

    props = described["properties"]
    if not props:
        console.print("[dim]No input properties documented for this endpoint.[/dim]")
        console.print()
    else:
        table = Table(show_header=True, header_style="bold cyan", title="Inputs (from live OpenAPI schema)")
        table.add_column("name")
        table.add_column("type")
        table.add_column("required")
        table.add_column("default")
        table.add_column("description / enum")
        for p in props:
            default = "" if p["default"] is None else _short(p["default"])
            desc = p["description"]
            if p["enum"]:
                desc = (desc + "  " if desc else "") + f"[dim]enum:[/dim] {', '.join(map(str, p['enum']))}"
            table.add_row(
                p["name"],
                p["type"],
                "[red]✓[/red]" if p["required"] else "",
                default,
                desc,
            )
        console.print(table)
        console.print()

    console.print("[bold]Global options:[/bold]")
    console.print("  -p, --prompt TEXT        Prompt (also pass via -i prompt=...). Use '-' for stdin.")
    console.print("  -i, --input KEY=VALUE    Repeatable. Values are parsed as JSON when valid.")
    console.print("  --input-file FILE        JSON file of inputs (merged before -i flags).")
    console.print("  --wait / --no-wait       Poll until done (default: --wait).")
    console.print("  --dry-run                Print the request that would be sent and exit.")
    console.print("  --download DIR, -d       Save outputs to DIR.")
    console.print("  --output-json, -j        Print raw JSON to stdout.")
    console.print("  --jq EXPR                jq-style filter on JSON output.")
    console.print()
    console.print("[dim]Example:[/dim] muapi run "
                  f"{model} -p \"...\" {_example_inputs(props)}--output-json")
    console.print()
    return True


def _short(val: object) -> str:
    s = repr(val) if isinstance(val, str) else str(val)
    return s if len(s) <= 32 else s[:29] + "..."


def _example_inputs(props: list[dict]) -> str:
    """Suggest a couple of `-i` flags from the schema as an example."""
    bits = []
    for p in props:
        if p["name"] == "prompt":
            continue
        if p["default"] is not None and not isinstance(p["default"], (list, dict)):
            bits.append(f"-i {p['name']}={p['default']}")
        elif p["enum"]:
            bits.append(f"-i {p['name']}={p['enum'][0]}")
        if len(bits) >= 2:
            break
    return (" ".join(bits) + " ") if bits else ""


def maybe_handle_run_help(argv: Optional[list[str]] = None) -> bool:
    """Top-level entry: if argv asks for `run <model> -h`, print + return True."""
    model = detect_run_help(list(argv) if argv is not None else sys.argv)
    if not model:
        return False
    return print_dynamic_help(model)
