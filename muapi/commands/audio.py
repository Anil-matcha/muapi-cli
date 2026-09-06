"""muapi audio — music creation and audio generation."""
from typing import Optional

import typer

from .. import client
from ..utils import console, download_outputs, error_exit, print_result, spinner_status

app = typer.Typer(help="Create and remix music and audio.")


@app.command("create")
def create(
    prompt: str = typer.Argument(..., help="Music description / lyrics prompt"),
    title: str = typer.Option("", "--title", "-t", help="Song title"),
    tags: str = typer.Option("", "--tags", help="Genre/style tags (comma-separated)"),
    instrumental: bool = typer.Option(False, "--instrumental", help="Generate without vocals"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Create original music with Suno."""
    payload = {
        "prompt": prompt,
        "title": title,
        "tags": tags,
        "make_instrumental": instrumental,
    }
    if webhook:
        payload["webhook_url"] = webhook
    try:
        with spinner_status("Creating music with Suno..."):
            result = client.generate("suno-create-music", payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e))

    print_result(result, output_json, label="Music (Suno)")
    if download and result.get("status") == "completed":
        download_outputs(result, download)


@app.command("remix")
def remix(
    song_id: str = typer.Argument(..., help="Suno song ID to remix"),
    prompt: str = typer.Option("", "--prompt", "-p", help="New style/lyric prompt"),
    title: str = typer.Option("", "--title", "-t"),
    tags: str = typer.Option("", "--tags"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Remix an existing Suno song."""
    payload = {"song_id": song_id, "prompt": prompt, "title": title, "tags": tags}
    if webhook:
        payload["webhook_url"] = webhook
    try:
        with spinner_status("Remixing with Suno..."):
            result = client.generate("suno-remix-music", payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e))

    print_result(result, output_json, label="Remix (Suno)")
    if download and result.get("status") == "completed":
        download_outputs(result, download)


@app.command("extend")
def extend(
    song_id: str = typer.Argument(..., help="Suno song ID to extend"),
    prompt: str = typer.Option("", "--prompt", "-p"),
    continue_at: float = typer.Option(0, "--continue-at", help="Time (seconds) to extend from"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Extend a Suno song."""
    payload = {"song_id": song_id, "prompt": prompt, "continue_at": continue_at}
    if webhook:
        payload["webhook_url"] = webhook
    try:
        with spinner_status("Extending with Suno..."):
            result = client.generate("suno-extend-music", payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e))

    print_result(result, output_json, label="Extended (Suno)")
    if download and result.get("status") == "completed":
        download_outputs(result, download)


@app.command("from-text")
def from_text(
    prompt: str = typer.Argument(..., help="Describe the audio to generate"),
    duration: float = typer.Option(10.0, "--duration", "-D", help="Duration in seconds"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Generate audio from text with MMAudio."""
    payload = {"prompt": prompt, "duration": duration}
    if webhook:
        payload["webhook_url"] = webhook
    try:
        with spinner_status("Generating audio with MMAudio..."):
            result = client.generate("mmaudio-v2/text-to-audio", payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e))

    print_result(result, output_json, label="Audio (MMAudio)")
    if download and result.get("status") == "completed":
        download_outputs(result, download)


@app.command("from-video")
def from_video(
    video_url: str = typer.Argument(..., help="Source video URL"),
    prompt: str = typer.Option("", "--prompt", "-p", help="Audio description prompt"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for async notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Add AI-generated audio to a video (MMAudio video-to-video)."""
    payload = {"video_url": video_url, "prompt": prompt}
    if webhook:
        payload["webhook_url"] = webhook
    try:
        with spinner_status("Generating audio for video with MMAudio..."):
            result = client.generate("mmaudio-v2/video-to-video", payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e))

    print_result(result, output_json, label="Video+Audio (MMAudio)")
    if download and result.get("status") == "completed":
        download_outputs(result, download)
