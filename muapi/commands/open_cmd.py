"""muapi open — open muapi.ai pages in your browser."""
import webbrowser
from typing import Optional

import typer

from ..utils import console, error_exit

_TARGETS: dict[str, str] = {
    "dashboard":   "https://muapi.ai/dashboard",
    "access-keys": "https://muapi.ai/access-keys",
    "models":      "https://muapi.ai/models",
    "docs":        "https://muapi.ai/docs",
    "pricing":     "https://muapi.ai/pricing",
    "api":         "https://api.muapi.ai/docs",
    "discord":     "https://discord.gg/muapi",
}


def open_page(
    target: Optional[str] = typer.Argument(
        None,
        help="Page to open: " + ", ".join(_TARGETS.keys()),
    ),
):
    """Open a muapi.ai page in your browser.

    \b
    Examples:
      muapi open               # opens dashboard
      muapi open access-keys   # key management
      muapi open models        # model catalog
      muapi open docs          # API docs
    """
    if not target:
        target = "dashboard"

    url = _TARGETS.get(target.lower())
    if not url:
        valid = ", ".join(_TARGETS.keys())
        error_exit(f"Unknown target '{target}'. Valid: {valid}")

    console.print(f"Opening [cyan]{url}[/cyan]")
    try:
        webbrowser.open(url)
    except Exception as e:
        error_exit(f"Could not open browser: {e}")
