"""MuapiAssetLoader — load a user's previously-generated muapi assets as
LangChain `Document`s for RAG / eval / "do another in that style" workflows.

Each document's `page_content` is the original prompt (or caption fallback);
`metadata` carries url, model, kind, request_id, created_at, credits.
"""
from __future__ import annotations

from typing import Iterator, Optional

try:
    from langchain_core.documents import Document
    from langchain_core.document_loaders import BaseLoader
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "langchain-core is required for MuapiAssetLoader. "
        "Install it with `pip install muapi-langchain` (langchain-core is a "
        "default dependency)."
    ) from e

from muapi import client as _cli


class MuapiAssetLoader(BaseLoader):
    """Load muapi-generated assets as Documents.

    Modes:

    * `request_ids=[...]` — load the assets produced by specific prediction
      request IDs. Useful for hydrating a chat session's generated media.
    * `kind="image" | "video" | "audio" | None` (default None) — when paired
      with the user's full asset history (server endpoint `/assets`), filter
      by modality. Falls back to per-request loading if the history endpoint
      isn't available.

    Example:
        from muapi_langchain.loader import MuapiAssetLoader
        loader = MuapiAssetLoader(request_ids=["abc123", "def456"])
        docs = loader.load()
    """

    def __init__(
        self,
        request_ids: Optional[list[str]] = None,
        kind: Optional[str] = None,
        limit: int = 50,
    ):
        self.request_ids = request_ids or []
        self.kind = kind
        self.limit = limit

    def lazy_load(self) -> Iterator[Document]:
        if self.request_ids:
            yield from self._load_by_ids()
            return
        yield from self._load_history()

    def _load_by_ids(self) -> Iterator[Document]:
        for rid in self.request_ids:
            try:
                result = _cli.get_result(rid)
            except Exception:
                continue
            yield self._to_document(result)

    def _load_history(self) -> Iterator[Document]:
        try:
            params = {"limit": self.limit}
            if self.kind:
                params["kind"] = self.kind
            history = _cli.post("assets/list", params)
        except Exception:
            return
        for item in history.get("items", []):
            yield self._to_document(item)

    def _to_document(self, result: dict) -> Document:
        outputs = result.get("outputs") or []
        if outputs and isinstance(outputs[0], dict):
            url = outputs[0].get("url") or outputs[0].get("video_url") or outputs[0].get("image_url")
        else:
            url = outputs[0] if outputs else None

        prompt = (
            result.get("prompt")
            or result.get("input", {}).get("prompt")
            or result.get("caption")
            or ""
        )
        return Document(
            page_content=prompt or "(no prompt recorded)",
            metadata={
                "source": url or "",
                "url": url,
                "model": result.get("model") or result.get("endpoint"),
                "kind": result.get("kind") or self.kind,
                "request_id": result.get("request_id") or result.get("id"),
                "created_at": result.get("created_at"),
                "credits": result.get("credits") or result.get("cost"),
            },
        )
