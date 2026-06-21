"""
ChromaDB persistence: one collection per session or namespaced ids.

Failure modes: empty collection, stale embeddings, wrong metric.
"""

from __future__ import annotations

from typing import Any

import chromadb


def get_client(persist_directory: str) -> chromadb.PersistentClient:
    """Return a Chroma PersistentClient."""
    return chromadb.PersistentClient(path=persist_directory)


def upsert_chunks(
    collection_name: str,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]] | None = None,
    *,
    persist_directory: str,
) -> None:
    """Add or update chunks with metadata for attribution."""
    client = get_client(persist_directory)
    coll = client.get_or_create_collection(name=collection_name)
    coll.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
