"""muapi image — text-to-image and image-to-image generation."""
from typing import Optional

import typer

from .. import client
from .. import exitcodes
from ..utils import (
    console, download_outputs, error_exit, print_result,
    print_dry_run, read_stdin_if_dash, spinner_status,
)

app = typer.Typer(help="Generate and edit images.")

# ── Model registries ───────────────────────────────────────────────────────────
# Short alias  →  actual muapi endpoint_url (must match server schema).

T2I_MODELS = {
    # Flux family
    "flux-dev":            "flux-dev-image",
    "flux-schnell":        "flux-schnell-image",
    "flux-krea":           "flux-krea-dev",
    "flux-kontext-dev":    "flux-kontext-dev-t2i",
    "flux-kontext-pro":    "flux-kontext-pro-t2i",
    "flux-kontext-max":    "flux-kontext-max-t2i",
    "flux-2-dev":          "flux-2-dev",
    "flux-2-pro":          "flux-2-pro",
    "flux-2-flex":         "flux-2-flex",
    "flux-2-klein-4b":     "flux-2-klein-4b",
    "flux-2-klein-9b":     "flux-2-klein-9b",
    # HiDream
    "hidream-fast":        "hidream_i1_fast_image",
    "hidream-dev":         "hidream_i1_dev_image",
    "hidream-full":        "hidream_i1_full_image",
    # Wan
    "wan2.1":              "wan2.1-text-to-image",
    "wan2.5":              "wan2.5-text-to-image",
    "wan2.6":              "wan2.6-text-to-image",
    "wan2.7":              "wan2.7-text-to-image",
    "wan2.7-pro":          "wan2.7-text-to-image-pro",
    # OpenAI / GPT-Image
    "gpt4o":               "gpt4o-text-to-image",
    "gpt-image":           "gpt-image-1.5",
    "gpt-image-2":         "gpt-image-2-text-to-image",
    # Google
    "imagen4":             "google-imagen4",
    "imagen4-fast":        "google-imagen4-fast",
    "imagen4-ultra":       "google-imagen4-ultra",
    # Midjourney
    "midjourney":          "midjourney-v7-text-to-image",
    "midjourney-v7":       "midjourney-v7",
    "midjourney-v8":       "midjourney-v8",
    "midjourney-niji":     "midjourney-niji",
    # Bytedance Seedream
    "seedream":            "bytedance-seedream-v4.5",
    "seedream-v3":         "bytedance-seedream-image",
    "seedream-v4":         "bytedance-seedream-v4",
    "seedream-v4.5":       "bytedance-seedream-v4.5",
    "seedream-5":          "seedream-5.0",
    # Qwen
    "qwen":                "qwen-image",
    "qwen-2":              "qwen-image-2.0",
    "qwen-2-pro":          "qwen-image-2.0-pro",
    # Nano-banana (Gemini-3 style)
    "nano-banana":         "nano-banana",
    "nano-banana-pro":     "nano-banana-pro",
    "nano-banana-2":       "nano-banana-2",
    # Kling
    "kling-o1":            "kling-o1-text-to-image",
    "kling-o3":            "kling-o3-image",
    # Hunyuan
    "hunyuan":             "hunyuan-image-2.1",
    "hunyuan-3":           "hunyuan-image-3.0",
    # Ideogram
    "ideogram":            "ideogram-v3-t2i",
    # Reve
    "reve":                "reve-text-to-image",
    # Z-Image
    "z-image":             "z-image-base",
    "z-image-turbo":       "z-image-turbo",
    # Leonardo
    "leonardo-lucid":      "leonardoai-lucid-origin",
    "leonardo-phoenix":    "leonardoai-phoenix-1.0",
    # Grok / xAI
    "grok":                "grok-imagine-text-to-image",
    "grok-quality":        "grok-imagine-text-to-image-quality",
    # Other
    "chroma":              "chroma-image",
    "sdxl":                "sdxl-image",
    "perfect-pony":        "perfect-pony-xl",
    "neta-lumina":         "neta-lumina",
}

# Models whose API takes width+height rather than aspect_ratio.
# Everything else defaults to aspect_ratio.
WIDTH_HEIGHT_MODELS = {
    "flux-dev", "flux-schnell", "flux-krea",
    "flux-2-dev", "flux-2-pro", "flux-2-flex",
    "flux-2-klein-4b", "flux-2-klein-9b",
    "hidream-fast", "hidream-dev", "hidream-full",
    "wan2.1",
    "sdxl", "perfect-pony", "neta-lumina",
}

I2I_MODELS = {
    # Flux Kontext (edit + effects)
    "flux-kontext-dev":     "flux-kontext-dev-i2i",
    "flux-kontext-pro":     "flux-kontext-pro-i2i",
    "flux-kontext-max":     "flux-kontext-max-i2i",
    "flux-kontext-effects": "flux-kontext-effects",
    # Flux 2 edit
    "flux-2-dev-edit":      "flux-2-dev-edit",
    "flux-2-pro-edit":      "flux-2-pro-edit",
    "flux-2-flex-edit":     "flux-2-flex-edit",
    "flux-2-klein-4b-edit": "flux-2-klein-4b-edit",
    "flux-2-klein-9b-edit": "flux-2-klein-9b-edit",
    # OpenAI / GPT
    "gpt4o":                "gpt4o-image-to-image",
    "gpt4o-edit":           "gpt4o-edit",
    "gpt-image-edit":       "gpt-image-1.5-edit",
    "gpt-image-2-edit":     "gpt-image-2-image-to-image",
    # Bytedance Seedream / Seededit
    "seededit":             "bytedance-seededit-image",
    "seedream-edit":        "bytedance-seedream-edit-v4",
    "seedream-v4.5-edit":   "bytedance-seedream-v4.5-edit",
    "seedream-5-edit":      "seedream-5.0-edit",
    "seedance-character":   "seedance-2-character",
    # Reve
    "reve":                 "reve-image-edit",
    # Midjourney
    "midjourney":           "midjourney-v7-image-to-image",
    "midjourney-style":     "midjourney-v7-style-reference",
    "midjourney-omni":      "midjourney-v7-omni-reference",
    # Qwen
    "qwen":                 "qwen-image-edit",
    "qwen-plus":            "qwen-image-edit-plus",
    "qwen-plus-lora":       "qwen-image-edit-plus-lora",
    "qwen-2511":            "qwen-image-edit-2511",
    "qwen-2-edit":          "qwen-image-2.0-edit",
    "qwen-2-pro-edit":      "qwen-image-2.0-pro-edit",
    # Nano-banana
    "nano-banana-edit":     "nano-banana-edit",
    "nano-banana-effects":  "nano-banana-effects",
    "nano-banana-2-edit":   "nano-banana-2-edit",
    "nano-banana-pro-edit": "nano-banana-pro-edit",
    # Kling
    "kling-o1-edit":        "kling-o1-edit-image",
    "kling-o3-edit":        "kling-o3-image-edit",
    # Wan
    "wan2.5-edit":          "wan2.5-image-edit",
    "wan2.6-edit":          "wan2.6-image-edit",
    "wan2.7-edit":          "wan2.7-image-edit",
    "wan2.7-edit-pro":      "wan2.7-image-edit-pro",
    # Ideogram
    "ideogram-character":   "ideogram-character",
    "ideogram-reframe":     "ideogram-v3-reframe",
    # Others
    "flux-redux":           "flux-redux",
    "flux-pulid":           "flux-pulid",
    "grok":                 "grok-imagine-image-to-image",
    "photo-pack":           "photo-pack",
    "portrait-stylist":     "portrait-stylist",
    "minimax-subject":      "minimax-01-subject-reference",
    "vidu-q2-ref":          "vidu-q2-reference-to-image",
}

# I2I models that send images via "images_list" (array) instead of "image_url".
LIST_INPUT_MODELS = {
    "flux-kontext-dev", "flux-kontext-pro", "flux-kontext-max", "flux-kontext-effects",
    "flux-2-dev-edit", "flux-2-pro-edit", "flux-2-flex-edit",
    "flux-2-klein-4b-edit", "flux-2-klein-9b-edit",
    "seedream-edit", "seedream-v4.5-edit", "seedream-5-edit", "seedance-character",
    "nano-banana-edit", "nano-banana-effects",
    "nano-banana-2-edit", "nano-banana-pro-edit",
    "qwen", "qwen-plus", "qwen-plus-lora", "qwen-2511",
    "qwen-2-edit", "qwen-2-pro-edit",
    "kling-o3-edit",
    "wan2.5-edit", "wan2.6-edit", "wan2.7-edit", "wan2.7-edit-pro",
    "vidu-q2-ref",
}


@app.command("generate")
def generate(
    prompt: str = typer.Argument(..., help="Text prompt. Pass '-' to read from stdin."),
    model: str = typer.Option("flux-dev", "--model", "-m",
                              help=f"Model. Choices: {', '.join(T2I_MODELS)}"),
    width: int       = typer.Option(1024, "--width", "-W"),
    height: int      = typer.Option(1024, "--height", "-H"),
    num_images: int  = typer.Option(1, "--num-images", "-n", min=1, max=4),
    aspect_ratio: str = typer.Option("1:1", "--aspect-ratio", "-a"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool       = typer.Option(True, "--wait/--no-wait", help="Poll until done"),
    dry_run: bool    = typer.Option(False, "--dry-run", help="Show request without executing"),
    download: Optional[str] = typer.Option(None, "--download", "-d", help="Download outputs to directory"),
    output_json: bool = typer.Option(False, "--output-json", "-j", help="Print raw JSON"),
    jq: Optional[str] = typer.Option(None, "--jq", help="jq-style filter on JSON output (e.g. '.outputs[0]')"),
):
    """Generate an image from a text prompt.

    Pipe-friendly: pass '-' as PROMPT to read from stdin.

    \b
    Examples:
      muapi image generate "a cyberpunk city" --model flux-dev
      echo "a cat" | muapi image generate -
      muapi image generate "sunset" --model nano-banana-pro --download ./out
      muapi image generate "logo" --output-json --jq '.outputs[0]'
    """
    prompt = read_stdin_if_dash(prompt)
    if model not in T2I_MODELS:
        error_exit(f"Unknown model '{model}'. Choices: {', '.join(T2I_MODELS)}", exitcodes.VALIDATION)
    endpoint = T2I_MODELS[model]

    payload: dict = {"prompt": prompt, "num_images": num_images}
    if model in WIDTH_HEIGHT_MODELS:
        payload["width"] = width
        payload["height"] = height
    else:
        payload["aspect_ratio"] = aspect_ratio
    if webhook:
        payload["webhook_url"] = webhook

    if dry_run:
        print_dry_run(endpoint, payload)
        return

    try:
        with spinner_status(f"Generating image with {model}..."):
            result = client.generate(endpoint, payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e), e.exit_code)

    print_result(result, output_json, label=f"Image ({model})", jq=jq)
    if download and result.get("status") == "completed":
        download_outputs(result, download)


@app.command("edit")
def edit(
    prompt: str = typer.Argument(..., help="Edit instruction. Pass '-' to read from stdin."),
    image: str  = typer.Option(..., "--image", "-i", help="Source image URL"),
    model: str  = typer.Option("flux-kontext-dev", "--model", "-m",
                               help=f"Model. Choices: {', '.join(I2I_MODELS)}"),
    aspect_ratio: str = typer.Option("1:1", "--aspect-ratio", "-a"),
    num_images: int   = typer.Option(1, "--num-images", "-n", min=1, max=4),
    webhook: Optional[str] = typer.Option(None, "--webhook"),
    wait: bool            = typer.Option(True, "--wait/--no-wait"),
    dry_run: bool         = typer.Option(False, "--dry-run"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
    jq: Optional[str] = typer.Option(None, "--jq"),
):
    """Edit an image using a prompt and reference image URL."""
    prompt = read_stdin_if_dash(prompt)
    if model not in I2I_MODELS:
        error_exit(f"Unknown model '{model}'. Choices: {', '.join(I2I_MODELS)}", exitcodes.VALIDATION)
    endpoint = I2I_MODELS[model]

    payload: dict = {"prompt": prompt, "aspect_ratio": aspect_ratio, "num_images": num_images}
    if model in LIST_INPUT_MODELS:
        payload["images_list"] = [image]
    else:
        payload["image_url"] = image
    if webhook:
        payload["webhook_url"] = webhook

    if dry_run:
        print_dry_run(endpoint, payload)
        return

    try:
        with spinner_status(f"Editing image with {model}..."):
            result = client.generate(endpoint, payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e), e.exit_code)

    print_result(result, output_json, label=f"Image Edit ({model})", jq=jq)
    if download and result.get("status") == "completed":
        download_outputs(result, download)


@app.command("models")
def list_models():
    """List all available image generation and editing models."""
    from rich.table import Table
    from ..utils import out

    t = Table(title="Image Models", show_header=True, header_style="bold magenta")
    t.add_column("Name", style="cyan")
    t.add_column("Type")
    t.add_column("Endpoint")
    for name, ep in T2I_MODELS.items():
        t.add_row(name, "text-to-image", ep)
    for name, ep in I2I_MODELS.items():
        t.add_row(name, "image-to-image", ep)
    out.print(t)
