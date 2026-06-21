"""Embedding calls for chunks — OpenAI embeddings or deterministic mock vectors."""

from __future__ import annotations

import hashlib
import math
import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumen.config import Settings

from lumen.config import get_settings
from lumen.llm.openai_compat import openai_client_for_embeddings

# text-embedding-3-small default dimension
_EMBEDDING_DIM = 1536


def _mock_embedding_vector(text: str, dim: int = _EMBEDDING_DIM) -> list[float]:
    """Deterministic unit vector for local pipeline runs without OpenAI embedding quota."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    out: list[float] = []
    counter = 0
    while len(out) < dim:
        block = hashlib.sha256(digest + counter.to_bytes(4, "big")).digest()
        for i in range(0, len(block) - 3, 4):
            if len(out) >= dim:
                break
            (w,) = struct.unpack_from("<f", block, i)
            out.append(float(w))
        counter += 1
    norm = math.sqrt(sum(x * x for x in out)) or 1.0
    return [x / norm for x in out]


def embed_texts(texts: list[str], *, settings: Settings | None = None) -> list[list[float]]:
    """Return embedding vectors in the same order as ``texts``."""
    s = settings or get_settings()
    if s.lumen_use_mock_embeddings or openai_client_for_embeddings(s) is None:
        return [_mock_embedding_vector(t) for t in texts]

    client = openai_client_for_embeddings(s)
    assert client is not None  # for type checkers
    out: list[list[float]] = []
    batch_size = 64
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = client.embeddings.create(model=s.lumen_embedding_model, input=batch)
        # API returns one item per input; preserve order by sorting on index if needed
        data = sorted(resp.data, key=lambda d: d.index)
        out.extend([list(d.embedding) for d in data])
    return out
