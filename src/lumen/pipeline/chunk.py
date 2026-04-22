"""Chunk text with overlap and stable ids for citation spans (week 2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_url: str
    text: str
    start_char: int
    end_char: int


def chunk_document(text: str, source_url: str, *, chunk_size: int = 1200, overlap: int = 200) -> list[Chunk]:
    """Split document into overlapping chunks with provenance."""
    raise NotImplementedError("Week 2: sliding window + stable ids.")
