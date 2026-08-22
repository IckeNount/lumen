"""
End-to-end research run: decompose → search → fetch → chunk → embed → retrieve →
contradictions → synthesize.

Session-scoped Chroma collection per ``session_id``.
"""

from __future__ import annotations

import re
import time
from collections.abc import Generator, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from lumen.config import get_settings
from lumen.pipeline.chunk import Chunk, chunk_document
from lumen.pipeline.contradictions import find_contradictions
from lumen.pipeline.decompose import decompose_question
from lumen.pipeline.embed import embed_texts
from lumen.pipeline.fetch import fetch_url
from lumen.pipeline.retrieve import retrieve
from lumen.pipeline.search import search_web
from lumen.pipeline.synthesize import (
    extract_key_findings,
    extract_report_body,
    iter_synthesize_report,
)
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
    """Final report and its structured evidence."""

    question: str
    key_findings: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    report_markdown: str
    sources: list[dict[str, Any]]
    uncertainty_notes: list[str]
    completed_at: str
    duration_ms: int


@dataclass(frozen=True)
class ResearchStage:
    """One honest pipeline stage update."""

    stage: str
    status: str
    message: str
    completed: int | None = None
    total: int | None = None


@dataclass(frozen=True)
class ResearchSourceFound:
    """A source successfully read during preparation."""

    source: dict[str, Any]


@dataclass(frozen=True)
class ResearchToken:
    """One streamed report fragment."""

    text: str


@dataclass(frozen=True)
class ResearchComplete:
    """The authoritative result from the current research run."""

    result: ResearchResult


ResearchStreamEvent = (
    ResearchStage | ResearchSourceFound | ResearchToken | ResearchComplete
)


@dataclass
class _Prepared:
    passages: list[dict[str, str]]
    sources: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    uncertainty_notes: list[str]


def _safe_collection_id(session_id: str, prefix: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", session_id).strip("_") or "session"
    return f"{prefix}_{safe}"[:256]


def _stage(
    stage: str,
    status: str,
    message: str,
    *,
    completed: int | None = None,
    total: int | None = None,
) -> ResearchStage:
    return ResearchStage(stage, status, message, completed, total)


def _source_summary(
    source_id: str,
    title: str,
    url: str,
    excerpt: str,
) -> dict[str, Any]:
    domain = urlsplit(url).netloc.removeprefix("www.")
    return {
        "id": source_id,
        "title": title or domain,
        "domain": domain,
        "url": url,
        "excerpt": excerpt[:320],
    }


def _iter_prepare(
    request: ResearchRequest,
) -> Generator[ResearchStage | ResearchSourceFound, None, _Prepared]:
    settings = get_settings()
    uncertainty: list[str] = []

    yield _stage("planning", "active", "Planning the investigation")
    subqs = decompose_question(
        request.question,
        max_subqueries=request.max_subqueries,
        settings=settings,
    )
    yield _stage(
        "planning",
        "complete",
        f"Planned {len(subqs)} research questions",
    )

    yield _stage("searching", "active", "Searching the web")
    hits_by_url: dict[str, tuple[str, str]] = {}
    for subquery in subqs:
        for hit in search_web(
            subquery,
            max_results=_MAX_HITS_PER_SUBQUERY,
            settings=settings,
        ):
            if hit.url and hit.url not in hits_by_url:
                hits_by_url[hit.url] = (hit.title, hit.snippet)
    yield _stage(
        "searching",
        "complete",
        f"Found {len(hits_by_url)} search results",
    )

    urls = list(hits_by_url)[:_MAX_FETCH_URLS]
    source_ids = {url: f"S{index}" for index, url in enumerate(urls, start=1)}
    all_chunks: list[Chunk] = []
    successful_fetches = 0
    fetch_failures = 0
    yield _stage(
        "reading",
        "active",
        "Reading sources",
        completed=0,
        total=len(urls),
    )
    for url in urls:
        try:
            text = fetch_url(url)
        except Exception:
            fetch_failures += 1
            uncertainty.append(f"Failed to fetch {url}")
            continue
        if not text.strip():
            fetch_failures += 1
            uncertainty.append(f"Empty text after fetch: {url}")
            continue
        successful_fetches += 1
        title = hits_by_url[url][0]
        yield ResearchSourceFound(
            _source_summary(source_ids[url], title, url, text)
        )
        all_chunks.extend(chunk_document(text, url))
    yield _stage(
        "reading",
        "warning" if fetch_failures else "complete",
        f"Read {successful_fetches} of {len(urls)} sources",
        completed=successful_fetches,
        total=len(urls),
    )

    if not all_chunks:
        uncertainty.append("No passages retrieved; expand search or check network.")
        return _Prepared([], [], [], uncertainty)

    yield _stage("comparing", "active", "Comparing claims")
    collection = _safe_collection_id(
        request.session_id,
        settings.chroma_collection_prefix,
    )
    ids = [chunk.chunk_id for chunk in all_chunks]
    documents = [chunk.text for chunk in all_chunks]
    metadata = [
        {"source_url": chunk.source_url, "chunk_id": chunk.chunk_id}
        for chunk in all_chunks
    ]
    vectors = embed_texts(documents, settings=settings)
    upsert_chunks(
        collection,
        ids,
        vectors,
        documents,
        metadata,
        persist_directory=settings.chroma_persist_directory,
    )

    query_vector = embed_texts([request.question], settings=settings)[0]
    top = min(settings.lumen_max_retrieval_chunks, 12)
    retrieved = retrieve(query_vector, collection, top_k=top, settings=settings)
    passages: list[dict[str, str]] = []
    source_records: dict[str, dict[str, Any]] = {}
    for passage in retrieved:
        source_id = source_ids.get(passage.source_url)
        if not source_id:
            continue
        passages.append(
            {
                "source_id": source_id,
                "chunk_id": passage.chunk_id,
                "source_url": passage.source_url,
                "text": passage.text,
            }
        )
        if source_id not in source_records:
            title = hits_by_url[passage.source_url][0]
            source_records[source_id] = _source_summary(
                source_id,
                title,
                passage.source_url,
                passage.text,
            )

    if not passages:
        uncertainty.append("No relevant passages retrieved after ranking.")

    contradictions = find_contradictions(passages, settings=settings)
    yield _stage(
        "comparing",
        "complete",
        f"Found {len(contradictions)} disagreements",
    )
    sources = sorted(source_records.values(), key=lambda source: int(source["id"][1:]))
    return _Prepared(passages, sources, contradictions, uncertainty)


def _result(
    request: ResearchRequest,
    prepared: _Prepared,
    report_markdown: str,
    *,
    started_at: float,
) -> ResearchResult:
    return ResearchResult(
        question=request.question,
        key_findings=extract_key_findings(report_markdown),
        contradictions=prepared.contradictions,
        report_markdown=extract_report_body(report_markdown) if report_markdown else "",
        sources=prepared.sources,
        uncertainty_notes=prepared.uncertainty_notes,
        completed_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=round((time.perf_counter() - started_at) * 1000),
    )


def iter_research(request: ResearchRequest) -> Iterator[ResearchStreamEvent]:
    """Stream progress and report fragments, then one authoritative result."""
    started_at = time.perf_counter()
    prepared = yield from _iter_prepare(request)
    if not prepared.passages:
        yield ResearchComplete(_result(request, prepared, "", started_at=started_at))
        return

    yield _stage("writing", "active", "Writing the report")
    report_parts: list[str] = []
    for piece in iter_synthesize_report(
        request.question,
        prepared.passages,
        settings=get_settings(),
    ):
        report_parts.append(piece)
        yield ResearchToken(piece)
    report = "".join(report_parts)
    yield ResearchComplete(_result(request, prepared, report, started_at=started_at))


def run_research(request: ResearchRequest) -> ResearchResult:
    """Execute the shared research stream and return its final result."""
    for event in iter_research(request):
        if isinstance(event, ResearchComplete):
            return event.result
    raise RuntimeError("research stream ended without a final result")


def iter_research_report_markdown(request: ResearchRequest) -> Iterator[str]:
    """Compatibility iterator for consumers that only need streamed report text."""
    for event in iter_research(request):
        if isinstance(event, ResearchToken):
            yield event.text
