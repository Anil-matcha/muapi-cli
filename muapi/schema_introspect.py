"""Fetch the muapi OpenAPI spec and resolve per-endpoint request schemas.

The CLI's static verb commands wrap a curated subset of models. `muapi run`
needs to reach *any* endpoint exposed by the API and discover its input
schema at call time — so we read the live OpenAPI spec and look up the
request body for the endpoint the user named.

The spec is cached on disk (~/.muapi/openapi-cache.json, 1h TTL) so repeated
`muapi run ... -h` calls don't hit the network.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from .config import BASE_URL

_HOST = BASE_URL.replace("/api/v1", "")
_OPENAPI_URL = f"{_HOST}/openapi.json"

_CACHE_DIR = Path.home() / ".muapi"
_CACHE_FILE = _CACHE_DIR / "openapi-cache.json"
_CACHE_TTL = 3600  # 1 hour, matches WaveSpeed's `models.json` cache

_API_PREFIX = "/api/v1/"


def _load_cache() -> Optional[dict]:
    if not _CACHE_FILE.exists():
        return None
    try:
        wrapper = json.loads(_CACHE_FILE.read_text())
        if time.time() - wrapper.get("fetched_at", 0) > _CACHE_TTL:
            return None
        if wrapper.get("base_url") != BASE_URL:
            return None
        return wrapper.get("spec")
    except Exception:
        return None


def _save_cache(spec: dict) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"base_url": BASE_URL, "fetched_at": time.time(), "spec": spec}
    try:
        _CACHE_FILE.write_text(json.dumps(payload))
    except Exception:
        pass  # cache failure shouldn't break the call


def fetch_spec(force_refresh: bool = False, timeout: float = 15.0) -> dict:
    """Return the OpenAPI spec, served from cache when fresh."""
    if not force_refresh:
        cached = _load_cache()
        if cached:
            return cached
    resp = httpx.get(_OPENAPI_URL, timeout=timeout)
    resp.raise_for_status()
    spec = resp.json()
    _save_cache(spec)
    return spec


# ── Lookup ────────────────────────────────────────────────────────────────────

def _resolve_ref(spec: dict, ref: str) -> dict:
    # "#/components/schemas/ImageRequest" → dict
    if not ref.startswith("#/"):
        return {}
    node: Any = spec
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            return {}
        node = node[part]
    return node if isinstance(node, dict) else {}


def find_endpoint(spec: dict, endpoint: str) -> Optional[dict]:
    """Locate the POST operation for an endpoint name (with or without /api/v1/ prefix)."""
    paths = spec.get("paths", {})
    # Try a few common forms — users pass the endpoint slug, not the full path.
    candidates = [endpoint]
    if not endpoint.startswith("/"):
        candidates.append(f"{_API_PREFIX}{endpoint}")
        candidates.append(f"/{endpoint}")
    for candidate in candidates:
        node = paths.get(candidate)
        if node and "post" in node:
            return node["post"]
    return None


def get_request_schema(spec: dict, endpoint: str) -> Optional[dict]:
    """Return the resolved JSON schema for the endpoint's request body, or None."""
    op = find_endpoint(spec, endpoint)
    if not op:
        return None
    body = op.get("requestBody", {})
    content = body.get("content", {}).get("application/json", {})
    schema = content.get("schema", {})
    # Follow a single $ref hop — that's all muapi's spec uses today.
    if "$ref" in schema:
        return _resolve_ref(spec, schema["$ref"])
    return schema or None


def _format_type(prop: dict) -> str:
    """Best-effort one-line type label for a JSON schema property."""
    if "enum" in prop:
        return "enum"
    if "anyOf" in prop:
        types = []
        for sub in prop["anyOf"]:
            t = sub.get("type")
            if t and t != "null":
                types.append(t)
        return " | ".join(types) if types else "any"
    if "type" in prop:
        t = prop["type"]
        if t == "array":
            item_type = prop.get("items", {}).get("type", "any")
            return f"array<{item_type}>"
        return t
    if "$ref" in prop:
        ref = prop["$ref"].rsplit("/", 1)[-1]
        return f"object<{ref}>"
    return "any"


def describe_schema(schema: dict) -> dict:
    """Normalize a JSON schema for display.

    Returns: {title, properties: [(name, type, required, default, enum, description)]}
    """
    title = schema.get("title", "")
    required = set(schema.get("required", []))
    rows = []
    for name, prop in schema.get("properties", {}).items():
        if not isinstance(prop, dict):
            continue
        rows.append({
            "name": name,
            "type": _format_type(prop),
            "required": name in required,
            "default": prop.get("default", None),
            "enum": prop.get("enum"),
            "description": prop.get("description") or prop.get("title") or "",
        })
    # Sort: required first, then alphabetical.
    rows.sort(key=lambda r: (not r["required"], r["name"]))
    return {"title": title, "properties": rows}


# ── Public convenience ───────────────────────────────────────────────────────

def lookup(endpoint: str, *, force_refresh: bool = False) -> Optional[dict]:
    """Fetch + extract + describe in one call. Returns None if not found."""
    spec = fetch_spec(force_refresh=force_refresh)
    schema = get_request_schema(spec, endpoint)
    if not schema:
        return None
    return describe_schema(schema)


def list_endpoint_slugs(spec: dict) -> list[str]:
    """Return every POST endpoint slug under /api/v1/."""
    slugs = []
    for path in spec.get("paths", {}):
        if path.startswith(_API_PREFIX) and "post" in spec["paths"][path]:
            slugs.append(path[len(_API_PREFIX):])
    return slugs
