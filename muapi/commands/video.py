"""muapi video — text-to-video and image-to-video generation."""
from typing import Optional

import typer

from .. import client, exitcodes
from ..utils import (
    console, download_outputs, error_exit, print_result,
    print_dry_run, read_stdin_if_dash, spinner_status,
)

app = typer.Typer(help="Generate videos from text or images.")

# ── Model registries ──────────────────────────────────────────────────────────
# Short alias  →  actual muapi endpoint_url (must match server schema).

T2V_MODELS = {
    # Veo
    "veo3":              "veo3-text-to-video",
    "veo3-fast":         "veo3-fast-text-to-video",
    "veo3.1":            "veo3.1-text-to-video",
    "veo3.1-fast":       "veo3.1-fast-text-to-video",
    "veo3.1-4k":         "veo3.1-4k-video",
    "veo3.1-lite":       "veo3.1-lite-text-to-video",
    "veo4":              "veo-4-text-to-video",
    # Kling
    "kling-master":      "kling-v2.1-master-t2v",
    "kling-v2.5-pro":    "kling-v2.5-turbo-pro-t2v",
    "kling-v2.6-pro":    "kling-v2.6-pro-t2v",
    "kling-v3-pro":      "kling-v3.0-pro-text-to-video",
    "kling-v3-std":      "kling-v3.0-standard-text-to-video",
    "kling-v3-4k":       "kling-v3.0-4k-text-to-video",
    "kling-v3-omni":     "kling-v3.0-omni-pro-text-to-video",
    "kling-v3-omni-std": "kling-v3.0-omni-standard-text-to-video",
    "kling-v3-omni-4k":  "kling-v3.0-omni-4k-text-to-video",
    "kling-o1":          "kling-o1-text-to-video",
    # Wan
    "wan2.1":            "wan2.1-text-to-video",
    "wan2.2":            "wan2.2-text-to-video",
    "wan2.2-5b-fast":    "wan2.2-5b-fast-t2v",
    "wan2.5":            "wan2.5-text-to-video",
    "wan2.5-fast":       "wan2.5-text-to-video-fast",
    "wan2.6":            "wan2.6-text-to-video",
    "wan2.7":            "wan2.7-text-to-video",
    # Seedance
    "seedance-pro":      "seedance-pro-t2v",
    "seedance-pro-fast": "seedance-pro-t2v-fast",
    "seedance-lite":     "seedance-lite-t2v",
    "seedance-v1.5":     "seedance-v1.5-pro-t2v",
    "seedance-v1.5-fast":"seedance-v1.5-pro-t2v-fast",
    "seedance-v2":       "seedance-v2.0-t2v",
    "seedance-2":        "seedance-2-text-to-video",
    "seedance-2-fast":   "seedance-2-text-to-video-fast",
    "seedance-2-vip":    "seedance-2-vip-text-to-video",
    "seedance-2-vip-fast":"seedance-2-vip-text-to-video-fast",
    # Hunyuan
    "hunyuan":           "hunyuan-text-to-video",
    "hunyuan-fast":      "hunyuan-fast-text-to-video",
    # Runway
    "runway":            "runway-text-to-video",
    # Pixverse
    "pixverse":          "pixverse-v4.5-t2v",
    "pixverse-v4.5":     "pixverse-v4.5-t2v",
    "pixverse-v5":       "pixverse-v5-t2v",
    "pixverse-v5.5":     "pixverse-v5.5-t2v",
    "pixverse-v6":       "pixverse-v6-t2v",
    # Vidu
    "vidu":              "vidu-v2.0-t2v",
    "vidu-q2-pro":       "vidu-q2-pro-text-to-video",
    "vidu-q2-turbo":     "vidu-q2-turbo-text-to-video",
    "vidu-q3-pro":       "vidu-q3-pro-text-to-video",
    "vidu-q3-turbo":     "vidu-q3-turbo-text-to-video",
    # MiniMax / Hailuo
    "minimax-std":       "minimax-hailuo-02-standard-t2v",
    "minimax-pro":       "minimax-hailuo-02-pro-t2v",
    "minimax-2.3-pro":   "minimax-hailuo-2.3-pro-t2v",
    "minimax-2.3-std":   "minimax-hailuo-2.3-standard-t2v",
    # LTX
    "ltx-2":             "ltx-2-pro-text-to-video",
    "ltx-2-fast":        "ltx-2-fast-text-to-video",
    "ltx-2-19b":         "ltx-2-19b-text-to-video",
    "ltx-2.3":           "ltx-2.3-text-to-video",
    # OpenAI Sora
    "sora":              "openai-sora",
    "sora-2":            "openai-sora-2-text-to-video",
    "sora-2-pro":        "openai-sora-2-pro-text-to-video",
    "sora-2-standard":   "openai-sora-2-standard-text-to-video",
    "sora-2-storyboard": "openai-sora-2-pro-storyboard",
    # Other
    "ovi":               "ovi-text-to-video",
    "grok":              "grok-imagine-text-to-video",
    "happy-horse":       "happy-horse-1-text-to-video-1080p",
    "happy-horse-720":   "happy-horse-1-text-to-video-720p",
}

I2V_MODELS = {
    # Veo
    "veo3":              "veo3-image-to-video",
    "veo3-fast":         "veo3-fast-image-to-video",
    "veo3.1":            "veo3.1-image-to-video",
    "veo3.1-fast":       "veo3.1-fast-image-to-video",
    "veo3.1-ref":        "veo3.1-reference-to-video",
    "veo3.1-lite":       "veo3.1-lite-image-to-video",
    "veo4":              "veo-4-image-to-video",
    # Kling
    "kling-std":         "kling-v2.1-standard-i2v",
    "kling-pro":         "kling-v2.1-pro-i2v",
    "kling-master":      "kling-v2.1-master-i2v",
    "kling-v2.5-pro":    "kling-v2.5-turbo-pro-i2v",
    "kling-v2.5-std":    "kling-v2.5-turbo-std-i2v",
    "kling-v2.6-pro":    "kling-v2.6-pro-i2v",
    "kling-v3-pro":      "kling-v3.0-pro-image-to-video",
    "kling-v3-std":      "kling-v3.0-standard-image-to-video",
    "kling-v3-4k":       "kling-v3.0-4k-image-to-video",
    "kling-v3-omni":     "kling-v3.0-omni-pro-image-to-video",
    "kling-v3-omni-std": "kling-v3.0-omni-standard-image-to-video",
    "kling-v3-omni-4k":  "kling-v3.0-omni-4k-image-to-video",
    "kling-o1":          "kling-o1-image-to-video",
    "kling-o1-std":      "kling-o1-standard-image-to-video",
    "kling-o1-ref":      "kling-o1-reference-to-video",
    # Wan
    "wan2.1":            "wan2.1-image-to-video",
    "wan2.1-ref":        "wan2.1-reference-video",
    "wan2.2":            "wan2.2-image-to-video",
    "wan2.2-spicy":      "wan2.2-spicy-image-to-video",
    "wan2.5":            "wan2.5-image-to-video",
    "wan2.5-fast":       "wan2.5-image-to-video-fast",
    "wan2.6":            "wan2.6-image-to-video",
    "wan2.7":            "wan2.7-image-to-video",
    "wan2.7-ref":        "wan2.7-reference-to-video",
    # Seedance
    "seedance-pro":      "seedance-pro-i2v",
    "seedance-pro-fast": "seedance-pro-i2v-fast",
    "seedance-lite":     "seedance-lite-i2v",
    "seedance-lite-ref": "seedance-lite-reference-to-video",
    "seedance-v1.5":     "seedance-v1.5-pro-i2v",
    "seedance-v1.5-fast":"seedance-v1.5-pro-i2v-fast",
    "seedance-v2":       "seedance-v2.0-i2v",
    "seedance-v2-omni":  "seedance-2.0-omni-reference",
    "seedance-2":        "seedance-2-image-to-video",
    "seedance-2-fast":   "seedance-2-image-to-video-fast",
    "seedance-2-flf":    "seedance-2-first-last-frame",
    "seedance-2-omni":   "seedance-2.0-omni-reference",
    "seedance-2-vip":    "seedance-2-vip-image-to-video",
    # Hunyuan
    "hunyuan":           "hunyuan-image-to-video",
    # Runway
    "runway":            "runway-image-to-video",
    "runway-act-two":    "runway-act-two-i2v",
    # Pixverse
    "pixverse-v4.5":     "pixverse-v4.5-i2v",
    "pixverse-v5":       "pixverse-v5-i2v",
    "pixverse-v5.5":     "pixverse-v5.5-i2v",
    "pixverse-v6":       "pixverse-v6-i2v",
    "pixverse-v6-trans": "pixverse-v6-transition",
    # Vidu
    "vidu":              "vidu-v2.0-i2v",
    "vidu-q1-ref":       "vidu-q1-reference",
    "vidu-q2-pro":       "vidu-q2-pro-image-to-video",
    "vidu-q2-turbo":     "vidu-q2-turbo-image-to-video",
    "vidu-q2-ref":       "vidu-q2-reference",
    "vidu-q2-start-end": "vidu-q2-pro-start-end-video",
    "vidu-q3-pro":       "vidu-q3-pro-image-to-video",
    "vidu-q3-turbo":     "vidu-q3-turbo-image-to-video",
    "vidu-q3-flf":       "vidu-q3-pro-first-last-frames",
    # Midjourney
    "midjourney":        "midjourney-v7-image-to-video",
    # MiniMax / Hailuo
    "minimax-std":       "minimax-hailuo-02-standard-i2v",
    "minimax-pro":       "minimax-hailuo-02-pro-i2v",
    "minimax-2.3-pro":   "minimax-hailuo-2.3-pro-i2v",
    "minimax-2.3-std":   "minimax-hailuo-2.3-standard-i2v",
    "minimax-2.3-fast":  "minimax-hailuo-2.3-fast",
    # LTX
    "ltx-2":             "ltx-2-pro-image-to-video",
    "ltx-2-fast":        "ltx-2-fast-image-to-video",
    "ltx-2-19b":         "ltx-2-19b-image-to-video",
    "ltx-2.3":           "ltx-2.3-image-to-video",
    # OpenAI Sora
    "sora-2":            "openai-sora-2-image-to-video",
    "sora-2-pro":        "openai-sora-2-pro-image-to-video",
    "sora-2-standard":   "openai-sora-2-standard-image-to-video",
    # Other
    "ovi":               "ovi-image-to-video",
    "grok":              "grok-imagine-image-to-video",
    "leonardo":          "leonardoai-motion-2.0",
    "happy-horse":       "happy-horse-1-image-to-video-1080p",
    "happy-horse-ref":   "happy-horse-1-reference-to-video-1080p",
    "infinitetalk":      "infinitetalk-image-to-video",
    "video-effects":     "video-effects",
    "wan-effects":       "generate_wan_ai_effects",
}

# I2V models that send images via "images_list" (array) instead of "image_url".
LIST_INPUT_I2V = {
    "wan2.1", "wan2.1-ref", "wan2.2", "wan2.2-spicy",
    "wan2.5", "wan2.5-fast", "wan2.6", "wan2.7", "wan2.7-ref",
    "seedance-pro", "seedance-pro-fast", "seedance-lite", "seedance-lite-ref",
    "seedance-v1.5", "seedance-v1.5-fast", "seedance-v2", "seedance-v2-omni",
    "seedance-2", "seedance-2-fast", "seedance-2-flf", "seedance-2-omni",
    "seedance-2-vip",
    "vidu", "vidu-q1-ref", "vidu-q2-pro", "vidu-q2-turbo", "vidu-q2-ref",
    "vidu-q2-start-end", "vidu-q3-pro", "vidu-q3-turbo", "vidu-q3-flf",
    "pixverse-v4.5", "pixverse-v5", "pixverse-v5.5", "pixverse-v6", "pixverse-v6-trans",
    "veo4",
    "sora-2", "sora-2-pro", "sora-2-standard",
    "kling-v3-4k", "kling-v3-omni", "kling-v3-omni-std", "kling-v3-omni-4k",
    "happy-horse", "happy-horse-ref",
}


@app.command("generate")
def generate(
    prompt: str = typer.Argument(..., help="Text prompt. Pass '-' to read from stdin."),
    model: str  = typer.Option("kling-master", "--model", "-m",
                               help=f"Model. Choices: {', '.join(T2V_MODELS)}"),
    duration: int     = typer.Option(5, "--duration", "-D", help="Duration in seconds"),
    aspect_ratio: str = typer.Option("16:9", "--aspect-ratio", "-a"),
    webhook: Optional[str] = typer.Option(None, "--webhook"),
    wait: bool    = typer.Option(True, "--wait/--no-wait"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
    jq: Optional[str] = typer.Option(None, "--jq"),
):
    """Generate a video from a text prompt.

    \b
    Examples:
      muapi video generate "a dog running on a beach" --model kling-master
      muapi video generate "ocean waves" --no-wait --output-json --jq '.request_id'
    """
    prompt = read_stdin_if_dash(prompt)
    if model not in T2V_MODELS:
        error_exit(f"Unknown model '{model}'. Choices: {', '.join(T2V_MODELS)}", exitcodes.VALIDATION)
    endpoint = T2V_MODELS[model]

    payload: dict = {"prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio}
    if webhook:
        payload["webhook_url"] = webhook

    if dry_run:
        print_dry_run(endpoint, payload)
        return

    try:
        with spinner_status(f"Generating video with {model}... (may take a while)"):
            result = client.generate(endpoint, payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e), e.exit_code)

    print_result(result, output_json, label=f"Video ({model})", jq=jq)
    if download and result.get("status") == "completed":
        download_outputs(result, download)


@app.command("from-image")
def from_image(
    prompt: str = typer.Argument(..., help="Motion/animation prompt. Pass '-' for stdin."),
    image: str  = typer.Option(..., "--image", "-i", help="Source image URL"),
    model: str  = typer.Option("kling-std", "--model", "-m",
                               help=f"Model. Choices: {', '.join(I2V_MODELS)}"),
    duration: int     = typer.Option(5, "--duration", "-D"),
    aspect_ratio: str = typer.Option("16:9", "--aspect-ratio", "-a"),
    webhook: Optional[str] = typer.Option(None, "--webhook"),
    wait: bool    = typer.Option(True, "--wait/--no-wait"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
    jq: Optional[str] = typer.Option(None, "--jq"),
):
    """Animate an image into a video."""
    prompt = read_stdin_if_dash(prompt)
    if model not in I2V_MODELS:
        error_exit(f"Unknown model '{model}'. Choices: {', '.join(I2V_MODELS)}", exitcodes.VALIDATION)
    endpoint = I2V_MODELS[model]

    payload: dict = {
        "prompt": prompt,
        "duration": duration, "aspect_ratio": aspect_ratio,
    }
    if model in LIST_INPUT_I2V:
        payload["images_list"] = [image]
    else:
        payload["image_url"] = image
    if webhook:
        payload["webhook_url"] = webhook

    if dry_run:
        print_dry_run(endpoint, payload)
        return

    try:
        with spinner_status(f"Animating image with {model}..."):
            result = client.generate(endpoint, payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e), e.exit_code)

    print_result(result, output_json, label=f"Image-to-Video ({model})", jq=jq)
    if download and result.get("status") == "completed":
        download_outputs(result, download)


@app.command("models")
def list_models():
    """List all available video generation models."""
    from rich.table import Table
    from ..utils import out

    t = Table(title="Video Models", show_header=True, header_style="bold magenta")
    t.add_column("Name", style="cyan")
    t.add_column("Type")
    t.add_column("Endpoint")
    for name, ep in T2V_MODELS.items():
        t.add_row(name, "text-to-video", ep)
    for name, ep in I2V_MODELS.items():
        t.add_row(name, "image-to-video", ep)
    out.print(t)
