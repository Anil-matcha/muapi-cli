"""muapi enhance — image/video enhancement tools."""
from typing import Optional

import typer

from .. import client
from ..utils import console, download_outputs, error_exit, print_result, spinner_status

app = typer.Typer(help="Enhance images and videos (upscale, bg-remove, face-swap, etc.).")


def _run(label: str, endpoint: str, payload: dict, wait: bool, download: Optional[str], output_json: bool):
    try:
        with spinner_status(f"{label}..."):
            result = client.generate(endpoint, payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e))
    print_result(result, output_json, label=label)
    if download and result.get("status") == "completed":
        download_outputs(result, download)


def _payload_with_webhook(payload: dict, webhook: Optional[str]) -> dict:
    if webhook:
        payload["webhook_url"] = webhook
    return payload


@app.command("upscale")
def upscale(
    image_url: str = typer.Argument(..., help="Image URL to upscale"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Upscale an image with AI."""
    _run("Upscaling image", "ai-image-upscale", _payload_with_webhook({"image_url": image_url}, webhook), wait, download, output_json)


@app.command("bg-remove")
def bg_remove(
    image_url: str = typer.Argument(..., help="Image URL"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Remove the background from an image."""
    _run("Removing background", "ai-background-remover", _payload_with_webhook({"image_url": image_url}, webhook), wait, download, output_json)


@app.command("face-swap")
def face_swap(
    source_url: str = typer.Option(..., "--source", "-s", help="Source face image URL"),
    target_url: str = typer.Option(..., "--target", "-t", help="Target image or video URL"),
    mode: str = typer.Option("image", "--mode", "-m", help="'image' or 'video'"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Swap faces in an image or video."""
    payload = _payload_with_webhook({"source_url": source_url, "target_url": target_url}, webhook)
    if mode == "video":
        _run("Face swapping in video", "ai-video-face-swap", payload, wait, download, output_json)
    else:
        _run("Face swapping in image", "ai-image-face-swap", payload, wait, download, output_json)


@app.command("skin")
def skin(
    image_url: str = typer.Argument(..., help="Image URL"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Enhance skin quality in a portrait image."""
    _run("Enhancing skin", "ai-skin-enhancer", _payload_with_webhook({"image_url": image_url}, webhook), wait, download, output_json)


@app.command("colorize")
def colorize(
    image_url: str = typer.Argument(..., help="Black & white image URL"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Colorize a black and white photo."""
    _run("Colorizing photo", "ai-color-photo", _payload_with_webhook({"image_url": image_url}, webhook), wait, download, output_json)


@app.command("ghibli")
def ghibli(
    image_url: str = typer.Argument(..., help="Image URL"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Convert an image to Ghibli anime style."""
    _run("Applying Ghibli style", "ai-ghibli-style", _payload_with_webhook({"image_url": image_url}, webhook), wait, download, output_json)


@app.command("anime")
def anime(
    image_url: str = typer.Argument(..., help="Image URL"),
    prompt: str = typer.Option("", "--prompt", "-p", help="Style prompt"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Convert an image to anime style."""
    _run("Generating anime style", "ai-anime-generator", _payload_with_webhook({"image_url": image_url, "prompt": prompt}, webhook), wait, download, output_json)


@app.command("extend")
def extend(
    image_url: str = typer.Argument(..., help="Image URL to extend/outpaint"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Extend/outpaint an image."""
    _run("Extending image", "ai-image-extension", _payload_with_webhook({"image_url": image_url}, webhook), wait, download, output_json)


@app.command("product-shot")
def product_shot(
    image_url: str = typer.Argument(..., help="Product image URL"),
    background_prompt: str = typer.Option("", "--bg", help="Background description"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Generate professional product photography."""
    payload = _payload_with_webhook({"image_url": image_url, "scene_description": background_prompt}, webhook)
    _run("Generating product shot", "ai-product-shot", payload, wait, download, output_json)


@app.command("erase")
def erase(
    image_url: str = typer.Argument(..., help="Image URL"),
    mask_url: str = typer.Option(..., "--mask", "-m", help="Mask image URL (white = erase area)"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Erase objects from an image using a mask."""
    payload = _payload_with_webhook({"image_url": image_url, "mask_image_url": mask_url}, webhook)
    _run("Erasing object", "ai-object-eraser", payload, wait, download, output_json)
