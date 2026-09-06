"""Thin sync wrapper around muapi-cli's HTTP client.

Adds the bits the tools need on top of the bare client:
  * uniform result-parsing into {url, urls, model, request_id, raw}
  * lightweight schema recovery — swaps image_url ↔ images_list and drops
    invalid aspect_ratio / duration fields when the server 422s. Mirrors
    the recovery loop the in-process creative agent uses.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

from muapi import client as _cli
from muapi.client import MuapiError

from ._registry import endpoint_for


_KIND_PAYLOAD_KEY: dict[str, str] = {
    "image_edit": "image_url",
    "i2v": "image_url",
    "lipsync": "video_url",
    "enhance": "image_url",
    "video_edit": "video_url",
}

_SAFE_RATIOS = {"1:1", "16:9", "9:16", "4:3", "3:4"}
_MAX_RECOVERY_ATTEMPTS = 3


def _try_recover_payload(payload: dict, error_body: str) -> Optional[dict]:
    """Mutate payload in response to a 422. Returns new payload, or None
    when no recovery is applicable (caller should re-raise)."""
    body = error_body or ""
    new = dict(payload)
    changed = False

    # image_url ↔ images_list swaps
    if "images_list" in body and "Field required" in body and "image_url" in new:
        new["images_list"] = [new.pop("image_url")]
        changed = True
    elif "image_url" in body and "Field required" in body and "images_list" in new:
        imgs = new.pop("images_list")
        if imgs:
            new["image_url"] = imgs[0]
            changed = True

    # video_url ↔ videos_list
    if "videos_list" in body and "Field required" in body and "video_url" in new:
        new["videos_list"] = [new.pop("video_url")]
        changed = True
    elif "video_url" in body and "Field required" in body and "videos_list" in new:
        vids = new.pop("videos_list")
        if vids:
            new["video_url"] = vids[0]
            changed = True

    # Drop unsupported aspect_ratio / duration on permissive models
    if "aspect_ratio" in body and new.get("aspect_ratio") not in _SAFE_RATIOS:
        new["aspect_ratio"] = "16:9"
        changed = True
    if "duration" in body and "duration" in new:
        new.pop("duration", None)
        changed = True

    return new if changed else None


def submit_and_wait(
    model: str,
    prompt: str,
    *,
    inputs: Optional[dict[str, Any]] = None,
    extra: Optional[dict[str, Any]] = None,
    timeout: int = 600,
) -> dict:
    """Submit a generation and return the parsed result.

    Returns: {url, urls, model, request_id, raw}
    """
    payload: dict[str, Any] = {"prompt": prompt} if prompt else {}
    if inputs:
        payload.update(inputs)
    if extra:
        payload.update(extra)

    endpoint = endpoint_for(model)
    attempt = 0
    while True:
        try:
            raw = _cli.generate(endpoint, payload, wait=True, poll_interval=3)
            break
        except MuapiError as exc:
            attempt += 1
            if attempt > _MAX_RECOVERY_ATTEMPTS or exc.status_code != 422:
                raise
            recovered = _try_recover_payload(payload, str(exc))
            if recovered is None:
                raise
            payload = recovered

    outputs = raw.get("outputs") or []
    if outputs and isinstance(outputs[0], dict):
        url = outputs[0].get("url") or outputs[0].get("video_url") or outputs[0].get("image_url")
        urls = [o.get("url") or o.get("video_url") or o.get("image_url") for o in outputs]
    else:
        url = outputs[0] if outputs else None
        urls = outputs
    return {
        "url": url,
        "urls": [u for u in urls if u],
        "model": model,
        # Sandbox / synchronous endpoints may return the completed payload
        # without an id; this is None in that case (not an error).
        "request_id": raw.get("request_id") or raw.get("id"),
        "raw": raw,
    }


def asset_input_key_for(kind: str) -> str:
    """The payload field name that carries a reference asset for this kind.
    submit_and_wait auto-swaps to the list variant on 422."""
    return _KIND_PAYLOAD_KEY.get(kind, "image_url")


def api_key_present() -> bool:
    from muapi.config import get_api_key
    return bool(os.environ.get("MUAPI_API_KEY") or get_api_key())
