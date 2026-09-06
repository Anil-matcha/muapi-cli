"""muapi run — generic, schema-driven runner for any muapi.ai model.

The curated `muapi image / video / audio / …` verbs each wrap one
endpoint with hand-picked flags. `run` is the escape hatch (and now the
default path) — pass any model/endpoint name plus `-i key=value` inputs
and it will POST whatever you give it.

Dynamic per-model help is handled before Typer parses (see main.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from .. import client, exitcodes, schema_introspect
from ..utils import (
    download_outputs, error_exit, print_result, print_dry_run,
    read_stdin_if_dash, spinner_status,
)

# `run` is registered as a single top-level command on the root Typer app
# (see muapi/main.py). It is *not* a subcommand group — the positional
# `model` argument needs to take the first slot after `muapi run`.


# ── Alias resolution ─────────────────────────────────────────────────────────
# Short, human names → real endpoint slugs. Populated lazily from the curated
# tables in the existing verb modules so we keep one source of truth.

def _build_alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}
    try:
        from .image import T2I_MODELS, I2I_MODELS
        # T2I wins over I2I when names collide — text-to-image is the more
        # common request for a bare alias.
        for k, v in I2I_MODELS.items():
            aliases.setdefault(k, v)
        for k, v in T2I_MODELS.items():
            aliases[k] = v
    except Exception:
        pass
    try:
        from .video import T2V_MODELS, I2V_MODELS
        for k, v in I2V_MODELS.items():
            aliases.setdefault(f"video:{k}", v)
        for k, v in T2V_MODELS.items():
            aliases.setdefault(f"video:{k}", v)
            aliases.setdefault(k, v)
    except Exception:
        pass
    return aliases


def resolve_model(model: str) -> str:
    """Resolve a model arg to an endpoint slug.

    If `model` looks like an endpoint slug (contains '-' or '/' or matches
    a known path), use it verbatim. Otherwise try the curated alias map.
    Unknown names are returned as-is so the server can give the real error.
    """
    if "/" in model:  # already a full path
        return model.lstrip("/")
    aliases = _build_alias_map()
    if model in aliases:
        return aliases[model]
    return model


# ── Input parsing ────────────────────────────────────────────────────────────

def _parse_kv(pair: str) -> tuple[str, object]:
    """Parse a `-i key=value` pair.

    Value is tried as JSON first (so `count=3`, `flag=true`, `arr=[1,2]`
    work) and falls back to a raw string.
    """
    if "=" not in pair:
        raise typer.BadParameter(f"-i expects key=value, got: {pair!r}")
    key, raw = pair.split("=", 1)
    key = key.strip()
    if not key:
        raise typer.BadParameter(f"-i has empty key: {pair!r}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = raw
    return key, value


def _load_input_file(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise typer.BadParameter(f"--input-file not found: {path}")
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"--input-file is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise typer.BadParameter("--input-file must contain a JSON object")
    return data


# ── The command ──────────────────────────────────────────────────────────────

def run(
    model: str = typer.Argument(
        ...,
        help="Model endpoint slug (e.g. 'flux-dev-image', 'nano-banana-2', 'seedance-2-text-to-video') or a curated alias.",
    ),
    prompt: Optional[str] = typer.Option(
        None, "-p", "--prompt",
        help="Prompt text. Pass '-' to read from stdin. Sets the 'prompt' field.",
    ),
    inputs: list[str] = typer.Option(
        [], "-i", "--input",
        help="Inputs as key=value (repeatable). JSON values are parsed (e.g. -i num_images=2 -i tags='[\"a\",\"b\"]').",
    ),
    input_file: Optional[str] = typer.Option(
        None, "--input-file",
        help="Path to a JSON file with inputs (merged before -i flags).",
    ),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Poll until done (default: --wait)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the request that would be sent and exit."),
    download: Optional[str] = typer.Option(None, "--download", "-d", help="Download outputs to directory."),
    output_json: bool = typer.Option(False, "--output-json", "-j", help="Print raw JSON to stdout."),
    jq: Optional[str] = typer.Option(None, "--jq", help="jq-style filter on JSON output (e.g. '.outputs[0]')."),
):
    """Run any muapi.ai model with arbitrary inputs.

    \b
    Examples:
      muapi run flux-dev-image -p "a cyberpunk skyline"
      muapi run nano-banana-2 -p "logo" -i num_images=2 --download ./out
      muapi run seedance-2-text-to-video -p "drone shot" -i duration=5 --output-json
      muapi run flux-kontext-pro-i2i -p "make it night" -i image_url=https://...

    \b
    Discover a model's inputs:
      muapi run <model> -h    # introspects the live OpenAPI schema

    \b
    Merge order for inputs (later wins):
      --input-file  <  -i key=value  <  -p prompt
    """
    endpoint = resolve_model(model)

    # Build payload: file < -i flags < --prompt
    payload: dict = {}
    if input_file:
        payload.update(_load_input_file(input_file))
    for pair in inputs:
        k, v = _parse_kv(pair)
        payload[k] = v
    if prompt is not None:
        payload["prompt"] = read_stdin_if_dash(prompt)

    if dry_run:
        print_dry_run(endpoint, payload)
        return

    try:
        with spinner_status(f"Running {endpoint}..."):
            result = client.generate(endpoint, payload, wait=wait)
    except client.MuapiError as e:
        error_exit(str(e), e.exit_code)

    print_result(result, output_json, label=f"Run ({endpoint})", jq=jq)
    if download and result.get("status") == "completed":
        download_outputs(result, download)
