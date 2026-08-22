"""
End-to-end research run: decompose → search → fetch → chunk → embed → retrieve →
contradictions → synthesize.

Session-scoped Chroma collection per ``session_id``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from lumen.config import get_settings
from lumen.pipeline.chunk import Chunk, chunk_document
from lumen.pipeline.contradictions import find_contradictions
from lumen.pipeline.decompose import decompose_question
from lumen.pipeline.embed import embed_texts
from lumen.pipeline.fetch import fetch_url
from lumen.pipeline.retrieve import retrieve
from lumen.pipeline.search import search_web
from lumen.pipeline.synthesize import iter_synthesize_report
from lumen.retrieval.chroma_store import upsert_chunks

_MAX_FETCH_URLS = 5
_MAX_HITS_PER_SUBQUERY = 5


@dataclass(frozen=True)
class ResearchRequest:
    """User-facing research query."""

    session_id: str
    question: str
    max_subqueries: int = 8


@dataclass
class ResearchResult:
    """Final artifact with report body and structured sidecars."""

    session_id: str
    report_markdown: str
    citations: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    uncertainty_notes: list[str]


@dataclass(frozen=True)
class ResearchToken:
    """One streamed report fragment."""

    text: str


@dataclass(frozen=True)
class ResearchComplete:
    """Structured sidecars and final report from the same research run."""

    result: ResearchResult


ResearchStreamEvent = ResearchToken | ResearchComplete


@dataclass
class _Prepared:
    passages: list[dict[str, str]]
    citations: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    uncertainty_notes: list[str]


def _safe_collection_id(session_id: str, prefix: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", session_id).strip("_") or "session"
    name = f"{prefix}_{safe}"
    return name[:256]


def _prepare(request: ResearchRequest) -> _Prepared:
    settings = get_settings()
    uncertainty: list[str] = []

    subqs = decompose_question(
        request.question,
        max_subqueries=request.max_subqueries,
        settings=settings,
    )
    hits_by_url: dict[str, tuple[str, str]] = {}
    for sq in subqs:
        for hit in search_web(sq, max_results=_MAX_HITS_PER_SUBQUERY, settings=settings):
            if hit.url and hit.url not in hits_by_url:
                hits_by_url[hit.url] = (hit.title, hit.snippet)

    urls = list(hits_by_url.keys())[:_MAX_FETCH_URLS]
    all_chunks: list[Chunk] = []
    for url in urls:
        try:
            text = fetch_url(url)
        except Exception:
            uncertainty.append(f"Failed to fetch {url}")
            continue
        if not text.strip():
            uncertainty.append(f"Empty text after fetch: {url}")
            continue
        all_chunks.extend(chunk_document(text, url))

    if not all_chunks:
        uncertainty.append("No passages retrieved; expand search or check network.")
        return _Prepared(
            passages=[],
            citations=[],
            contradictions=[],
            uncertainty_notes=uncertainty,
        )

    coll = _safe_collection_id(request.session_id, settings.chroma_collection_prefix)
    ids = [c.chunk_id for c in all_chunks]
    docs = [c.text for c in all_chunks]
    metas = [{"source_url": c.source_url, "chunk_id": c.chunk_id} for c in all_chunks]
    vectors = embed_texts(docs, settings=settings)
    upsert_chunks(
        coll,
        ids,
        vectors,
        docs,
        metas,
        persist_directory=settings.chroma_persist_directory,
    )

    qvec = embed_texts([request.question], settings=settings)[0]
    top = min(settings.lumen_max_retrieval_chunks, 12)
    retrieved = retrieve(qvec, coll, top_k=top, settings=settings)
    passages = [
        {"chunk_id": r.chunk_id, "source_url": r.source_url, "text": r.text} for r in retrieved
    ]
    citations: list[dict[str, Any]] = [
        {"chunk_id": r.chunk_id, "source_url": r.source_url, "score": r.score} for r in retrieved
    ]
    contra = find_contradictions(passages, settings=settings)
    return _Prepared(
        passages=passages,
        citations=citations,
        contradictions=contra,
        uncertainty_notes=uncertainty,
    )


def iter_research(request: ResearchRequest) -> Iterator[ResearchStreamEvent]:
    """Stream report fragments and finish with metadata from the same run."""
    prep = _prepare(request)
    if not prep.passages:
        report = "No sources available to synthesize an answer."
        yield ResearchToken(f"{report}\n")
        for note in prep.uncertainty_notes:
            yield ResearchToken(f"\n*Note:* {note}\n")
        yield ResearchComplete(
            ResearchResult(
                session_id=request.session_id,
                report_markdown=report,
                citations=prep.citations,
                contradictions=prep.contradictions,
                uncertainty_notes=prep.uncertainty_notes,
            )
        )
        return

    report_parts: list[str] = []
    for piece in iter_synthesize_report(
        request.question, prep.passages, settings=get_settings()
    ):
        report_parts.append(piece)
        yield ResearchToken(piece)
    yield ResearchComplete(
        ResearchResult(
            session_id=request.session_id,
            report_markdown="".join(report_parts),
            citations=prep.citations,
            contradictions=prep.contradictions,
            uncertainty_notes=prep.uncertainty_notes,
        )
    )


def run_research(request: ResearchRequest) -> ResearchResult:
    """Execute the shared research stream and return its final result."""
    for event in iter_research(request):
        if isinstance(event, ResearchComplete):
            return event.result
    raise RuntimeError("research stream ended without a final result")


def iter_research_report_markdown(request: ResearchRequest) -> Iterator[str]:
    """Compatibility iterator for callers that only consume report text."""
    for event in iter_research(request):
        if isinstance(event, ResearchToken):
            yield event.text
