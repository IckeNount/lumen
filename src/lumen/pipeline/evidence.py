"""Model-free source acquisition and semantic evidence retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from lumen.config import Settings

from lumen.config import get_settings
from lumen.pipeline.chunk import Chunk, chunk_document
from lumen.pipeline.embed import embed_texts_locally
from lumen.pipeline.fetch import fetch_url
from lumen.pipeline.retrieve import retrieve
from lumen.pipeline.search import search_web
from lumen.retrieval.chroma_store import upsert_chunks


@dataclass(frozen=True)
class EvidencePassage:
    """One retrieved passage with stable response-local attribution."""

    source_id: str
    url: str
    text: str
    score: float


@dataclass(frozen=True)
class EvidenceResult:
    """Structured evidence for a host model to reason over."""

    question: str
    evidence: list[EvidencePassage]
    uncertainty: list[str]


class EvidencePipelineError(RuntimeError):
    """Actionable failure at one evidence-pipeline stage."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"{stage} failure: {message}")


def _run_collection_name(session_id: str | None, prefix: str) -> str:
    safe_prefix = re.sub(r"[^a-zA-Z0-9_-]+", "_", prefix).strip("_")[:20] or "lumen"
    safe_session = re.sub(r"[^a-zA-Z0-9_-]+", "_", session_id or "run").strip("_")[:16] or "run"
    return f"{safe_prefix}_evidence_{safe_session}_{uuid4().hex[:8]}"[:63]


def research_evidence(
    question: str,
    *,
    session_id: str | None = None,
    max_sources: int = 5,
    settings: Settings | None = None,
) -> EvidenceResult:
    """Search once and return semantically retrieved evidence without LLM calls."""
    query = question.strip()
    if not query:
        raise ValueError("question must not be empty")
    if not 1 <= max_sources <= 10:
        raise ValueError("max_sources must be between 1 and 10")

    runtime_settings = settings or get_settings()
    uncertainty: list[str] = []

    try:
        hits = search_web(query, max_results=max_sources, settings=runtime_settings)
    except Exception as exc:
        raise EvidencePipelineError("search", str(exc)) from exc

    urls: list[str] = []
    seen_urls: set[str] = set()
    for hit in hits:
        if hit.url and hit.url not in seen_urls:
            seen_urls.add(hit.url)
            urls.append(hit.url)
        if len(urls) >= max_sources:
            break

    chunks: list[Chunk] = []
    for url in urls:
        try:
            text = fetch_url(url)
        except Exception as exc:
            uncertainty.append(f"Failed to fetch {url}: {exc}")
            continue
        if not text.strip():
            uncertainty.append(f"Empty text after fetch: {url}")
            continue
        chunks.extend(chunk_document(text, url))

    if not chunks:
        uncertainty.append("No source text was available for retrieval.")
        return EvidenceResult(question=query, evidence=[], uncertainty=uncertainty)

    try:
        document_vectors = embed_texts_locally([chunk.text for chunk in chunks])
        query_vector = embed_texts_locally([query])[0]
    except Exception as exc:
        raise EvidencePipelineError("embedding", str(exc)) from exc

    collection_name = _run_collection_name(session_id, runtime_settings.chroma_collection_prefix)
    try:
        upsert_chunks(
            collection_name,
            [chunk.chunk_id for chunk in chunks],
            document_vectors,
            [chunk.text for chunk in chunks],
            [
                {"source_url": chunk.source_url, "chunk_id": chunk.chunk_id}
                for chunk in chunks
            ],
            persist_directory=runtime_settings.chroma_persist_directory,
        )
        passages = retrieve(
            query_vector,
            collection_name,
            top_k=min(max_sources, runtime_settings.lumen_max_retrieval_chunks),
            settings=runtime_settings,
        )
    except Exception as exc:
        raise EvidencePipelineError("retrieval", str(exc)) from exc

    evidence = [
        EvidencePassage(
            source_id=f"S{index}",
            url=passage.source_url,
            text=passage.text,
            score=passage.score,
        )
        for index, passage in enumerate(passages, start=1)
    ]
    return EvidenceResult(question=query, evidence=evidence, uncertainty=uncertainty)
