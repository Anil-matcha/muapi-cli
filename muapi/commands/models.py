"""muapi models — global model discovery across all media types."""
import typer
from rich.table import Table

from ..utils import out
from .image import T2I_MODELS, I2I_MODELS
from .video import T2V_MODELS, I2V_MODELS

app = typer.Typer(help="Discover available models across all categories.")

_ALL_MODELS = {
    "image:text-to-image":  T2I_MODELS,
    "image:image-to-image": I2I_MODELS,
    "video:text-to-video":  T2V_MODELS,
    "video:image-to-video": I2V_MODELS,
    "audio": {
        "suno":      "suno-create-music",
        "mmaudio":   "mmaudio-v2/text-to-audio",
    },
    "enhance": {
        "upscale":      "ai-image-upscale",
        "bg-remove":    "ai-background-remover",
        "face-swap":    "ai-image-face-swap / ai-video-face-swap",
        "skin":         "ai-skin-enhancer",
        "colorize":     "ai-color-photo",
        "ghibli":       "ai-ghibli-style",
        "anime":        "ai-anime-generator",
        "extend":       "ai-image-extension",
        "product-shot": "ai-product-shot",
        "erase":        "ai-object-eraser",
    },
    "edit": {
        "effects":   "video-effects / image-effects / wan-effects",
        "lipsync":   "sync / latentsync / creatify / veed",
        "dance":     "dance",
        "dress":     "ai-dress-change",
        "clipping":  "ai-clipping",
    },
}


@app.command("list")
def list_models(
    category: str = typer.Option("all", "--category", "-c",
                                 help="Filter by category: image, video, audio, enhance, edit, all"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """List all available models and endpoints.

    \b
    Examples:
      muapi models list
      muapi models list --category video
      muapi models list --output-json | jq 'keys'
    """
    if output_json:
        import json
        # Flatten to list of {name, category, endpoint}
        rows = []
        for cat, models in _ALL_MODELS.items():
            if category != "all" and not cat.startswith(category):
                continue
            for name, ep in models.items():
                rows.append({"name": name, "category": cat, "endpoint": ep})
        out.print_json(json.dumps(rows))
        return

    t = Table(title="muapi Models", show_header=True, header_style="bold magenta")
    t.add_column("Category", style="dim")
    t.add_column("Name", style="cyan")
    t.add_column("Endpoint")

    for cat, models in _ALL_MODELS.items():
        if category != "all" and not cat.startswith(category):
            continue
        for name, ep in models.items():
            t.add_row(cat, name, ep)

    out.print(t)
