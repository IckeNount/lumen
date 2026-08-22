"""Lightweight tests for chunking and mock embeddings (no network)."""

from __future__ import annotations

import math

from lumen.pipeline.chunk import chunk_document
from lumen.pipeline.embed import embed_texts
from lumen.pipeline.retrieve import _similarity_score
from lumen.config import Settings


def test_chunk_document_overlap() -> None:
    text = "word " * 500
    chunks = chunk_document(text, "https://example.com/doc", chunk_size=200, overlap=40)
    assert len(chunks) >= 2
    assert all(c.source_url == "https://example.com/doc" for c in chunks)
    assert chunks[0].start_char == 0


def test_embed_texts_mock() -> None:
    s = Settings.model_construct(lumen_use_mock_embeddings=True)
    vectors = embed_texts(["alpha", "beta"], settings=s)
    assert len(vectors) == 2
    assert len(vectors[0]) == 1536
    assert all(math.isfinite(value) for vector in vectors for value in vector)
    assert all(
        math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0)
        for vector in vectors
    )


def test_similarity_score_rejects_non_finite_distances() -> None:
    assert _similarity_score(float("nan")) == 0.0
    assert _similarity_score(float("inf")) == 0.0
    assert _similarity_score(-1.0) == 0.0
    assert _similarity_score(1.0) == 0.5
