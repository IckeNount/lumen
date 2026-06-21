"""Query embeddings and retrieve top-k chunks with scores."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from chromadb.errors import NotFoundError

if TYPE_CHECKING:
    from lumen.config import Settings

from lumen.config import get_settings
from lumen.retrieval.chroma_store import get_client


@dataclass(frozen=True)
class RetrievedPassage:
    chunk_id: str
    source_url: str
    text: str
    score: float


def retrieve(
    query_embedding: list[float],
    session_collection: str,
    *,
    top_k: int = 12,
    settings: Settings | None = None,
) -> list[RetrievedPassage]:
    """Vector similarity search in session-scoped Chroma collection."""
    s = settings or get_settings()
    client = get_client(s.chroma_persist_directory)
    try:
        coll = client.get_collection(name=session_collection)
    except (ValueError, NotFoundError):
        return []

    n_docs = coll.count()
    if n_docs == 0:
        return []

    result = coll.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, n_docs),
    )
    ids = (result.get("ids") or [[]])[0]
    docs = (result.get("documents") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]
    metas: list[Any] = (result.get("metadatas") or [[]])[0]

    passages: list[RetrievedPassage] = []
    for i, chunk_id in enumerate(ids):
        meta = metas[i] if i < len(metas) and metas[i] else {}
        url = str(meta.get("source_url") or "")
        text = docs[i] if i < len(docs) else ""
        dist = float(dists[i]) if i < len(dists) else 0.0
        # Chroma L2 distance: lower is better; expose similarity-like score
        score = 1.0 / (1.0 + dist)
        passages.append(
            RetrievedPassage(chunk_id=str(chunk_id), source_url=url, text=str(text), score=score)
        )
    return passages
