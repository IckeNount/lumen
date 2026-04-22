"""
ChromaDB persistence: one collection per session or namespaced ids (week 2).

Failure modes to document in wiki: empty collection, stale embeddings, wrong metric.
"""

from __future__ import annotations

from typing import Any


def get_client(persist_directory: str) -> Any:
    """Return a Chroma PersistentClient — implementation in week 2."""
    raise NotImplementedError("Week 2: chromadb.PersistentClient + collection lifecycle.")


def upsert_chunks(
    collection_name: str,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]] | None = None,
) -> None:
    """Add or update chunks with metadata for attribution."""
    raise NotImplementedError("Week 2: batch upsert + idempotency.")
