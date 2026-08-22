"""Lightweight tests for chunking and mock embeddings (no network)."""

from __future__ import annotations

import math
import json
from types import SimpleNamespace

import pytest

from lumen.pipeline.chunk import chunk_document
from lumen.pipeline.contradictions import find_contradictions
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


def test_contradictions_keep_only_valid_source_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "items": [
            {
                "kind": "direct_conflict",
                "topic": "Outcome",
                "claim_a": {"text": "Alpha wins", "source_ids": ["S1", "S9"]},
                "claim_b": {"text": "Beta wins", "source_ids": ["S2"]},
                "explanation": "Different results.",
                "unresolved": None,
            },
            {
                "kind": "direct_conflict",
                "topic": "Unsupported",
                "claim_a": {"text": "Unknown", "source_ids": ["S9"]},
                "claim_b": {"text": "Beta", "source_ids": ["S2"]},
                "explanation": "Invalid source.",
                "unresolved": None,
            },
        ]
    }
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))
        ]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: completion)
        )
    )
    monkeypatch.setattr(
        "lumen.pipeline.contradictions.build_openai_client",
        lambda settings: client,
    )
    settings = Settings.model_construct(lumen_chat_model="test")

    result = find_contradictions(
        [
            {"source_id": "S1", "chunk_id": "c1", "source_url": "a", "text": "A"},
            {"source_id": "S2", "chunk_id": "c2", "source_url": "b", "text": "B"},
        ],
        settings=settings,
    )

    assert len(result) == 1
    assert result[0]["id"] == "C1"
    assert result[0]["claim_a"]["source_ids"] == ["S1"]
