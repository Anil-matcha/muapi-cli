"""The 4 LangChain tools that expose muapi to a Deep Agent (or any agent).

The tools form a capability gradient — cheap discovery → cheap execute →
named workflow → open-ended planning — so a Deep Agent can split them
between a planner and a specialist subagent:

    Planner (cheap, info-only):
        muapi_select        — discover models + skills, no credits
        muapi_generate      — single-shot generation, any modality

    Specialist (heavy, stateful):
        muapi_run_skill     — named multi-step workflow (UGC ad, storyboard…)
        muapi_creative_agent — open-ended planning + execution, HITL-gated

Each tool returns a structured `dict`-as-`str` so the agent can ingest and
re-emit the urls / asset metadata without losing structure.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from langchain_core.tools import tool

from ._client import asset_input_key_for, submit_and_wait
from ._registry import (
    default_model_for,
    find_skill,
    shortlist_models,
    shortlist_skills,
)


# ── 1. discovery / inspection (planner tier) ─────────────────────────────────

@tool
def muapi_select(
    intent: str,
    kind: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = 5,
) -> str:
    """Discover muapi models and skills for a brief — free, no credits spent.

    Use this FIRST when you don't know which model/skill fits, or to budget
    a multi-step plan before calling muapi_generate / muapi_run_skill.

    Args:
        intent: Plain-English description of what the user wants.
        kind: Optional filter — one of "image", "image_edit", "video", "i2v",
            "video_edit", "lipsync", "audio", "enhance", "3d".
        tier: Optional filter — "best", "balanced", "fast", or "budget".
        limit: How many candidates per category (default 5).

    Returns:
        JSON string with `models` (ranked candidates) and `skills` (named
        recipes that match the intent).
    """
    return json.dumps({
        "intent": intent,
        "kind": kind,
        "tier": tier,
        "models": shortlist_models(intent, kind=kind, tier=tier, limit=limit),
        "skills": shortlist_skills(intent, limit=limit),
    })


# ── 2. single-shot generation (planner tier) ─────────────────────────────────

@tool
def muapi_generate(
    prompt: str,
    kind: str = "image",
    model: str = "auto",
    input_asset_url: Optional[str] = None,
    tier: str = "balanced",
    extra: Optional[dict[str, Any]] = None,
) -> str:
    """Generate ONE media asset via muapi (image / video / audio / edit / enhance).

    Use this for a single, clear ask. Costs credits. For multi-step asks
    (story, campaign, multi-asset packs), use muapi_creative_agent or a
    matching muapi_run_skill instead.

    Args:
        prompt: The user's prompt or instruction.
        kind: The modality. One of:
            "image", "video", "audio",
            "image_edit", "i2v", "video_edit", "lipsync", "enhance".
        model: A specific registry model name (e.g. "flux-kontext-pro-t2i"),
            or "auto" to let muapi pick based on `kind` + `tier`.
            Run `muapi_select` first to discover good model names.
        input_asset_url: Reference asset URL — required for edit / i2v /
            lipsync / enhance kinds.
        tier: When `model="auto"`, which quality tier to pick
            ("best" / "balanced" / "fast" / "budget"). Default "balanced".
        extra: Optional dict merged into the generation payload (model-specific
            params like aspect_ratio, duration, seed).

    Returns:
        JSON string: {ok, url, model, kind, request_id, source_asset_url}
    """
    if model == "auto":
        picked = default_model_for(kind, tier)
        if not picked:
            return json.dumps({"ok": False, "error": f"no default model for kind={kind!r} tier={tier!r}"})
        model = picked

    inputs: dict[str, Any] = {}
    if input_asset_url:
        inputs[asset_input_key_for(kind)] = input_asset_url

    try:
        result = submit_and_wait(model, prompt, inputs=inputs, extra=extra)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc), "model": model, "kind": kind})

    return json.dumps({
        "ok": True,
        "url": result["url"],
        "model": result["model"],
        "kind": kind,
        "request_id": result["request_id"],
        "source_asset_url": input_asset_url,
    })


# ── 3. named workflow (specialist tier) ──────────────────────────────────────

@tool
def muapi_run_skill(skill_name: str, inputs: dict[str, Any]) -> str:
    """Run a named muapi skill — a pre-baked multi-step recipe (e.g.
    "ugc-ads-workflow", "storyboard", "product-ad-cinematic").

    Skills bundle several generation calls into a deterministic workflow.
    Use `muapi_select` to discover skill names and their required inputs,
    then call this with the inputs filled in.

    Args:
        skill_name: One of the skill names returned by muapi_select.
        inputs: A dict of the skill's declared inputs. Required keys come
            from the skill's `inputs` schema.

    Returns:
        JSON string: {ok, skill, assets, total_credits_est, message}
    """
    skill = find_skill(skill_name)
    if not skill:
        return json.dumps({
            "ok": False,
            "error": f"unknown skill {skill_name!r}",
            "hint": "Call muapi_select to list available skills.",
        })

    # v1: route skills through the server-side creative agent (it knows how to
    # interpret skill markdown). Falls back to a stub if the server endpoint
    # isn't deployed yet, so the tool surface is stable today.
    try:
        from muapi import client as _cli
        payload = {
            "brief": f"Run skill {skill_name} with inputs: {json.dumps(inputs)}",
            "skill": skill_name,
            "inputs": inputs,
        }
        raw = _cli.post("agent/skill/run", payload)
    except Exception as exc:
        return json.dumps({
            "ok": False,
            "skill": skill_name,
            "error": f"server skill runner not available: {exc}",
            "estimated_credits": skill.get("estimated_credits"),
            "note": "Pass `skill_name` + `inputs` to muapi_creative_agent as a fallback.",
        })

    return json.dumps({
        "ok": True,
        "skill": skill_name,
        "assets": raw.get("assets", []),
        "total_credits_est": skill.get("estimated_credits"),
        "raw": raw,
    })


# ── 4. open-ended creative agent (specialist tier, HITL-gated) ───────────────

@tool
def muapi_creative_agent(brief: str, budget_credits: int = 300) -> str:
    """Hand a multi-asset brief to muapi's creative agent — it will plan and
    execute a DAG of generation calls (e.g. "make a 30s product story with
    visuals and music").

    This tool can spend significant credits. Wrap it with `interrupt_on`
    in your Deep Agent config so a human approves the plan before execution.

    Args:
        brief: Plain-English description of the desired output.
        budget_credits: Hard cap on credits the agent may spend. The agent
            will refuse plans whose estimate exceeds this.

    Returns:
        JSON string: {ok, plan_summary, assets, credits_spent}
    """
    try:
        from muapi import client as _cli
        raw = _cli.post("agent/creative/run", {
            "brief": brief,
            "budget_credits": budget_credits,
        })
    except Exception as exc:
        return json.dumps({
            "ok": False,
            "error": f"creative agent endpoint unavailable: {exc}",
            "hint": "Decompose with muapi_select + multiple muapi_generate calls instead.",
        })

    return json.dumps({
        "ok": True,
        "plan_summary": raw.get("plan_summary"),
        "assets": raw.get("assets", []),
        "credits_spent": raw.get("credits_spent"),
        "raw": raw,
    })


# Convenience exports for splitting tools across planner / specialist
PLANNER_TOOLS = [muapi_select, muapi_generate]
SPECIALIST_TOOLS = [muapi_run_skill, muapi_creative_agent]
ALL_TOOLS = PLANNER_TOOLS + SPECIALIST_TOOLS
