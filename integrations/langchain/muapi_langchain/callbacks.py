"""MuapiCostCallback — tracks credits spent by muapi tool calls and enforces
an optional budget.

LangChain callbacks fire around every tool invocation. We inspect each
muapi tool's JSON-string output, parse out `credits` / `credits_spent`
fields, accumulate, and raise `BudgetExceeded` once a cap is hit.

Usage:
    cb = MuapiCostCallback(budget_credits=500, on_event=print)
    agent.invoke({"messages": [...]}, config={"callbacks": [cb]})
    print(cb.total_credits, cb.breakdown)
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError as e:  # pragma: no cover
    raise ImportError("langchain-core is required for MuapiCostCallback.") from e


# Rough static credit estimates per kind/model when the tool result doesn't
# include an explicit cost. Used so a Deep Agent can still reason about
# spend even before the server starts echoing back exact credits.
_FALLBACK_CREDITS = {
    "image": 6,
    "image_edit": 8,
    "video": 60,
    "i2v": 60,
    "video_edit": 40,
    "lipsync": 20,
    "audio": 12,
    "enhance": 8,
    "3d": 25,
}


class BudgetExceeded(RuntimeError):
    """Raised when accumulated muapi spend passes the configured budget."""


class MuapiCostCallback(BaseCallbackHandler):
    """Track muapi credit spend across a LangChain / LangGraph run.

    Args:
        budget_credits: Optional hard cap. When set, the callback raises
            BudgetExceeded inside on_tool_end if the cumulative spend
            crosses it. The exception propagates into the agent thread so
            the run aborts cleanly.
        on_event: Optional callback fired with (event_name, payload). Useful
            for piping spend updates into LangSmith / your UI in real time.
    """

    def __init__(
        self,
        budget_credits: Optional[int] = None,
        on_event: Optional[Callable[[str, dict], None]] = None,
    ):
        self.budget_credits = budget_credits
        self.on_event = on_event
        self.total_credits: int = 0
        self.breakdown: list[dict] = []

    # ── LangChain BaseCallbackHandler hooks ──────────────────────────────────

    def on_tool_end(self, output: Any, *, name: str = "", **kwargs: Any) -> None:
        if not name.startswith("muapi_"):
            return
        cost = self._extract_cost(output, name)
        if cost <= 0:
            return
        self.total_credits += cost
        entry = {"tool": name, "credits": cost, "running_total": self.total_credits}
        self.breakdown.append(entry)
        if self.on_event:
            try:
                self.on_event("muapi.spend", entry)
            except Exception:
                pass
        if self.budget_credits is not None and self.total_credits > self.budget_credits:
            raise BudgetExceeded(
                f"muapi budget of {self.budget_credits} credits exceeded "
                f"({self.total_credits} spent across {len(self.breakdown)} calls)"
            )

    # ── internals ────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_cost(output: Any, tool_name: str) -> int:
        """Pull a credit count from a muapi tool result. Falls back to a
        per-kind static estimate when the result has no explicit cost."""
        data: dict[str, Any]
        if isinstance(output, dict):
            data = output
        elif isinstance(output, str):
            try:
                data = json.loads(output)
            except (json.JSONDecodeError, ValueError):
                return 0
        else:
            return 0

        if not data.get("ok", True):
            return 0

        for key in ("credits", "credits_spent", "total_credits_est"):
            if key in data and isinstance(data[key], (int, float)):
                return int(data[key])

        if tool_name == "muapi_generate":
            return _FALLBACK_CREDITS.get(data.get("kind") or "image", 6)
        if tool_name == "muapi_run_skill":
            return _FALLBACK_CREDITS.get("video", 60)  # skills tend to be multi-step
        if tool_name == "muapi_creative_agent":
            return 0  # the agent reports its own credits_spent; trust nothing else
        return 0

    # ── summary helpers ──────────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "total_credits": self.total_credits,
            "calls": len(self.breakdown),
            "by_tool": self._by_tool(),
            "breakdown": self.breakdown,
        }

    def _by_tool(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for entry in self.breakdown:
            out[entry["tool"]] = out.get(entry["tool"], 0) + entry["credits"]
        return out
