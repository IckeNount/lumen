"""Embedding calls for chunks — provider-agnostic wrapper (week 2)."""

from __future__ import annotations


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return embedding vectors in the same order as `texts`."""
    raise NotImplementedError("Week 2: OpenAI embeddings batching + error handling.")
