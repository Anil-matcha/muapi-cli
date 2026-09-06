"""muapi predict — check and wait for async prediction results."""
from typing import Optional

import typer

from .. import client, exitcodes
from ..utils import console, download_outputs, error_exit, print_result, spinner_status

app = typer.Typer(help="Check or wait for async prediction results.")


@app.command("result")
def result(
    request_id: str = typer.Argument(..., help="Prediction request ID"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
    jq: Optional[str] = typer.Option(None, "--jq", help="jq-style filter on output (e.g. '.outputs[0]')"),
):
    """Fetch the current result of a prediction (no polling)."""
    try:
        data = client.get_result(request_id)
    except client.MuapiError as e:
        error_exit(str(e), e.exit_code)
    print_result(data, output_json, label=f"Prediction {request_id}", jq=jq)


@app.command("wait")
def wait(
    request_id: str = typer.Argument(..., help="Prediction request ID"),
    timeout: int = typer.Option(600, "--timeout", "-T", help="Max wait time in seconds"),
    download: Optional[str] = typer.Option(None, "--download", "-d"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
    jq: Optional[str] = typer.Option(None, "--jq"),
):
    """Wait for a prediction to complete, then show the result."""
    try:
        with spinner_status(f"Waiting for prediction {request_id}..."):
            data = client.wait_for_result(request_id, max_seconds=timeout)
    except client.MuapiError as e:
        error_exit(str(e), e.exit_code)

    print_result(data, output_json, label=f"Prediction {request_id}", jq=jq)
    if download and data.get("status") == "completed":
        download_outputs(data, download)
