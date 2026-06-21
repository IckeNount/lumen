"""Chunk text with overlap and stable ids for citation spans."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_url: str
    text: str
    start_char: int
    end_char: int


def _url_fingerprint(source_url: str) -> str:
    return hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:12]


def chunk_document(text: str, source_url: str, *, chunk_size: int = 1200, overlap: int = 200) -> list[Chunk]:
    """Split document into overlapping chunks with provenance."""
    if not text.strip():
        return []

    fp = _url_fingerprint(source_url)
    chunks: list[Chunk] = []
    step = max(1, chunk_size - overlap)
    pos = 0
    idx = 0
    while pos < len(text):
        end = min(pos + chunk_size, len(text))
        piece = text[pos:end]
        chunk_id = f"{fp}_{idx}"
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                source_url=source_url,
                text=piece,
                start_char=pos,
                end_char=end,
            )
        )
        if end >= len(text):
            break
        pos += step
        idx += 1
    return chunks
