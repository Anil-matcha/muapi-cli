"""Runnable Deep Agent demo using the muapi-langchain integration.

The pattern: a planner with cheap muapi tools (select + generate), and a
`creative-specialist` subagent that gets the heavy multi-step tools
(run_skill, creative_agent). Open-ended creative work is gated behind
human approval via `interrupt_on`.

Run:
    export MUAPI_API_KEY="..."        # or muapi auth configure
    export OPENAI_API_KEY="..."
    pip install "git+https://github.com/SamurAIGPT/muapi-cli.git#subdirectory=integrations/langchain"
    pip install deepagents langgraph langchain-openai
    python deep_agents_demo.py
"""
from __future__ import annotations

import os
import uuid

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from muapi_langchain import (
    MuapiCostCallback,
    SPECIALIST_TOOLS,
    PLANNER_TOOLS,
    muapi_creative_agent,
    muapi_run_skill,
    muapi_select,
    muapi_generate,
)


CREATIVE_SPECIALIST = {
    "name": "creative-specialist",
    "description": (
        "Handles multi-step muapi workflows: named skills (UGC ads, "
        "storyboards, product videos) and open-ended creative briefs that "
        "decompose into a DAG of generation calls."
    ),
    "system_prompt": (
        "You are a muapi creative specialist. "
        "Prefer muapi_run_skill when the user's brief matches a named recipe "
        "(call muapi_select first to find the right skill). "
        "Escalate to muapi_creative_agent only for open-ended multi-asset "
        "briefs that don't match a skill. "
        "Return concise summaries including asset URLs."
    ),
    "tools": SPECIALIST_TOOLS,
}


def build_agent():
    return create_deep_agent(
        model=ChatOpenAI(
            model=os.environ.get("MUAPI_DEMO_MODEL", "gpt-4o"),
            api_key=os.environ["OPENAI_API_KEY"],
        ),
        tools=PLANNER_TOOLS,
        subagents=[CREATIVE_SPECIALIST],
        system_prompt=(
            "You are a creative-media Deep Agent backed by muapi. "
            "Always start with muapi_select to discover which models/skills "
            "fit the user's brief and to estimate cost. "
            "For a single image/video/audio ask, call muapi_generate yourself. "
            "Delegate multi-step or named-workflow asks to the "
            "creative-specialist subagent."
        ),
        # Gate expensive open-ended planning behind explicit human approval.
        interrupt_on={
            "muapi_creative_agent": {"allowed_decisions": ["approve", "edit", "reject"]},
        },
        checkpointer=MemorySaver(),
    )


def run(brief: str, budget_credits: int = 500) -> None:
    agent = build_agent()
    cost_cb = MuapiCostCallback(
        budget_credits=budget_credits,
        on_event=lambda evt, payload: print(f"[{evt}] {payload}"),
    )
    config = {"configurable": {"thread_id": str(uuid.uuid4())}, "callbacks": [cost_cb]}

    result = agent.invoke(
        {"messages": [{"role": "user", "content": brief}]},
        config=config,
        version="v2",
    )

    while getattr(result, "interrupts", None):
        action = result.interrupts[0].value["action_requests"][0]
        print(f"\n— APPROVAL REQUIRED —\nTool: {action['name']}\nArgs: {action['args']}")
        decision = input("approve / edit / reject: ").strip().lower() or "reject"
        result = agent.invoke(
            Command(resume={"decisions": [{"type": decision}]}),
            config=config,
            version="v2",
        )

    print("\n— FINAL MESSAGES —")
    for msg in result["messages"][-3:]:
        print(f"[{msg.type}]", getattr(msg, "content", ""))
    print("\n— SPEND SUMMARY —")
    print(cost_cb.summary())


if __name__ == "__main__":
    run(
        brief=(
            "Make a 3-shot Instagram carousel for a new mango-flavored sparkling "
            "water called 'SunFizz'. Cinematic product photography, sunny vibe."
        ),
        budget_credits=300,
    )
