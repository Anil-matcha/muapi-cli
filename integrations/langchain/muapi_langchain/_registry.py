"""Vendored muapi model + skill registry. Reads JSON snapshots shipped with
the package so the integration has zero runtime dependency on the muapiapp
server source. Regenerate via scripts/refresh_registry.py."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources
from typing import Iterable, Optional


CATEGORY_FOR_KIND: dict[str, str] = {
    "image": "text-to-image",
    "image_edit": "image-edit",
    "video": "text-to-video",
    "i2v": "image-to-video",
    "video_edit": "video-edit",
    "lipsync": "lipsync",
    "avatar": "avatar",
    "audio": "audio",
    "enhance": "enhance",
    "3d": "3d",
}

TIER_BIAS = {"balanced": 3, "best": 2, "fast": 1, "budget": 0}

# Registry-name → API path. Names not listed here are used as-is.
PATH_OVERRIDES: dict[str, str] = {
    "flux-dev": "flux-dev-image",
    "flux-schnell": "flux-schnell-image",
    "flux-dev-lora": "flux_dev_lora_image",
    "sdxl-lora": "sdxl-lora-image",
    "hidream-i1-fast": "hidream_i1_fast_image",
    "hidream-i1-dev": "hidream_i1_dev_image",
    "hidream-i1-full": "hidream_i1_full_image",
    "ai-image-upscaler": "ai-image-upscale",
    "mmaudio-v2-text-to-audio": "mmaudio-v2/text-to-audio",
    "mmaudio-v2-video-to-video": "mmaudio-v2/video-to-video",
    "bytedance-seedream-v3": "bytedance-seedream-image",
    "bytedance-seededit-v3": "bytedance-seededit-image",
    "bytedance-seedream-v4-edit": "bytedance-seedream-edit-v4",
    "latent-sync": "latentsync-video",
    "any-llm": "any-llm-models",
}


def endpoint_for(model: str) -> str:
    """Translate a registry model name to the wire endpoint path."""
    return PATH_OVERRIDES.get(model, model)


@lru_cache(maxsize=1)
def _load_models() -> list[dict]:
    with resources.files("muapi_langchain.data").joinpath("models.json").open() as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_skills() -> list[dict]:
    with resources.files("muapi_langchain.data").joinpath("skills.json").open() as f:
        return json.load(f)


def all_models() -> list[dict]:
    return list(_load_models())


def all_skills() -> list[dict]:
    return list(_load_skills())


_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


def shortlist_models(
    intent: str,
    kind: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = 5,
) -> list[dict]:
    """Rank models by keyword overlap with `intent`, filtered by kind + tier.

    Returns a list of `{name, description, category, tier, score}` dicts.
    """
    pool = _load_models()
    if kind:
        target = CATEGORY_FOR_KIND.get(kind, kind)
        pool = [m for m in pool if m.get("category") == target]
    if tier:
        pool = [m for m in pool if m.get("tier") == tier]

    query = _tokens(intent)
    scored: list[tuple[float, dict]] = []
    for m in pool:
        desc_tokens = _tokens(m.get("description", ""))
        name_tokens = _tokens(m.get("name", "").replace("-", " "))
        overlap = len(query & (desc_tokens | name_tokens))
        bias = TIER_BIAS.get(m.get("tier", ""), 0) * 0.1
        score = overlap + bias
        if score > 0 or not query:
            scored.append((score, m))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        {
            "name": m["name"],
            "description": m["description"],
            "category": m.get("category"),
            "tier": m.get("tier"),
            "score": round(s, 2),
        }
        for s, m in scored[:limit]
    ]


def shortlist_skills(intent: str, limit: int = 5) -> list[dict]:
    """Rank skills by overlap with `intent`, considering trigger_keywords too."""
    query = _tokens(intent)
    scored: list[tuple[float, dict]] = []
    for sk in _load_skills():
        haystack = " ".join(
            [sk.get("name", ""), sk.get("description", "")]
            + (sk.get("trigger_keywords") or [])
        )
        overlap = len(query & _tokens(haystack))
        if overlap > 0 or not query:
            scored.append((overlap, sk))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        {
            "name": sk["name"],
            "description": sk["description"],
            "inputs": sk.get("inputs", []),
            "estimated_credits": sk.get("estimated_credits"),
            "score": s,
        }
        for s, sk in scored[:limit]
    ]


def find_skill(name: str) -> Optional[dict]:
    for sk in _load_skills():
        if sk.get("name") == name:
            return sk
    return None


def default_model_for(kind: str, tier: str = "balanced") -> Optional[str]:
    """Pick a sensible default model for a kind+tier when caller passes auto.
    Names match the registry name (which may be remapped by PATH_OVERRIDES)."""
    DEFAULTS = {
        ("image", "balanced"): "flux-kontext-pro-t2i",
        ("image", "fast"): "flux-schnell",
        ("image", "best"): "flux-kontext-max-t2i",
        ("image", "budget"): "flux-schnell",
        ("image_edit", "balanced"): "flux-kontext-pro-i2i",
        ("image_edit", "best"): "flux-kontext-max-i2i",
        ("video", "balanced"): "seedance-pro-t2v",
        ("video", "fast"): "seedance-lite-t2v",
        ("video", "best"): "veo3",
        ("video", "budget"): "seedance-lite-t2v",
        ("i2v", "balanced"): "kling-v3.0-standard-image-to-video",
        ("i2v", "best"): "veo3-image-to-video",
        ("audio", "balanced"): "suno-create",
        ("enhance", "balanced"): "ai-image-upscaler",
    }
    if (kind, tier) in DEFAULTS:
        return DEFAULTS[(kind, tier)]
    return DEFAULTS.get((kind, "balanced"))
