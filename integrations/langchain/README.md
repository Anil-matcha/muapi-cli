# muapi-langchain

LangChain integration for [muapi.ai](https://muapi.ai) — 250+ generative
media models behind a single key, exposed as LangChain tools, a document
loader, and a Deep Agents recipe.

## Install

```bash
pip install muapi-langchain

# For the Deep Agents demo:
pip install "muapi-langchain[deepagents]"
```

Or install directly from the repo (latest main):

```bash
pip install "git+https://github.com/SamurAIGPT/muapi-cli.git#subdirectory=integrations/langchain"
```

Set your API key:

```bash
export MUAPI_API_KEY="..."     # or: muapi auth configure
```

## What's in the box

### 4 tools (capability gradient)

| Tool                    | What it does                                         | Costs credits? |
| ----------------------- | ---------------------------------------------------- | -------------- |
| `muapi_select`          | Rank models + skills for an intent                   | No             |
| `muapi_generate`        | Single-shot generation (image / video / audio / edit)| Yes (per call) |
| `muapi_run_skill`       | Named multi-step recipe (UGC ad, storyboard, …)      | Yes (recipe)   |
| `muapi_creative_agent`  | Open-ended brief → planner → executor                | Yes (variable) |

```python
from muapi_langchain import muapi_select, muapi_generate

print(muapi_select.invoke({
    "intent": "cinematic product photo of a sneaker",
    "kind": "image", "tier": "best", "limit": 3,
}))

print(muapi_generate.invoke({
    "prompt": "A glossy sneaker on a wet street at neon-lit night",
    "kind": "image", "tier": "best",
}))
```

### `MuapiAssetLoader` — document loader

Hydrate prior muapi generations as `Document`s for RAG / eval.

```python
from muapi_langchain import MuapiAssetLoader

docs = MuapiAssetLoader(request_ids=["req_abc", "req_def"]).load()
for d in docs:
    print(d.metadata["url"], "·", d.page_content[:80])
```

### `MuapiCostCallback` — budget tracking

Pipe every muapi tool call through a callback that accumulates credit spend
and aborts the agent when a budget cap is hit.

```python
from muapi_langchain import MuapiCostCallback

cost_cb = MuapiCostCallback(
    budget_credits=500,
    on_event=lambda evt, payload: print(evt, payload),
)
agent.invoke({...}, config={"callbacks": [cost_cb]})
print(cost_cb.summary())
```

## Deep Agents recipe

The recommended pattern: cheap tools (`select`, `generate`) on the main
planner, heavy tools (`run_skill`, `creative_agent`) on a
`creative-specialist` subagent, with `interrupt_on` for human approval of
open-ended creative work.

See [`examples/deep_agents_demo.py`](examples/deep_agents_demo.py) for the
full runnable example.

```python
from deepagents import create_deep_agent
from muapi_langchain import PLANNER_TOOLS, SPECIALIST_TOOLS

agent = create_deep_agent(
    model=...,
    tools=PLANNER_TOOLS,
    subagents=[{
        "name": "creative-specialist",
        "description": "Heavy muapi workflows and open-ended briefs.",
        "system_prompt": "...",
        "tools": SPECIALIST_TOOLS,
    }],
    interrupt_on={
        "muapi_creative_agent": {"allowed_decisions": ["approve", "edit", "reject"]},
    },
)
```

## Decision tree

```
User brief
  ├─ Don't know which model/skill?  → muapi_select          (free)
  ├─ Single asset, clear prompt?    → muapi_generate
  ├─ Matches a known recipe?        → muapi_run_skill
  └─ Multi-asset / multi-modal?     → muapi_creative_agent  (interrupt_on)
```

## License

MIT.
