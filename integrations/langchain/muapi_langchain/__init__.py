"""LangChain integration for muapi.ai.

Public surface:

    Tools (use with any agent framework):
        from muapi_langchain import (
            muapi_select,
            muapi_generate,
            muapi_run_skill,
            muapi_creative_agent,
            PLANNER_TOOLS,
            SPECIALIST_TOOLS,
            ALL_TOOLS,
        )

    Document loader:
        from muapi_langchain import MuapiAssetLoader

    Callback (spend tracking + budget cap):
        from muapi_langchain import MuapiCostCallback, BudgetExceeded
"""
from .tools import (
    ALL_TOOLS,
    PLANNER_TOOLS,
    SPECIALIST_TOOLS,
    muapi_creative_agent,
    muapi_generate,
    muapi_run_skill,
    muapi_select,
)
from .loader import MuapiAssetLoader
from .callbacks import BudgetExceeded, MuapiCostCallback

__version__ = "0.1.0"

__all__ = [
    "muapi_select",
    "muapi_generate",
    "muapi_run_skill",
    "muapi_creative_agent",
    "PLANNER_TOOLS",
    "SPECIALIST_TOOLS",
    "ALL_TOOLS",
    "MuapiAssetLoader",
    "MuapiCostCallback",
    "BudgetExceeded",
    "__version__",
]
