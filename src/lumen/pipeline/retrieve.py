"""Query embeddings and retrieve top-k chunks with scores (week 2)."""

from __future__ import annotations

from dataclasses import dataclass


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
) -> list[RetrievedPassage]:
    """Vector similarity search in session-scoped Chroma collection."""
    raise NotImplementedError("Week 2: Chroma query + attribution payload.")
