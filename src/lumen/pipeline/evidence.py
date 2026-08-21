"""Model-free source acquisition and semantic evidence retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

if TYPE_CHECKING:
    from lumen.config import Settings

from lumen.config import get_settings
from lumen.pipeline.chunk import Chunk, chunk_document
from lumen.pipeline.embed import embed_texts_locally
from lumen.pipeline.fetch import fetch_url
from lumen.pipeline.retrieve import RetrievedPassage, retrieve
from lumen.pipeline.search import search_web
from lumen.retrieval.chroma_store import upsert_chunks

_LOW_CONFIDENCE_SCORE = 0.45
_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
_LOCATION_HINT = re.compile(
    r"\b(?:in|within|across|from)\s+(?:the\s+)?"
    r"([A-Z][A-Za-z'-]*(?:\s+[A-Z][A-Za-z'-]*){0,2})(?=[?.,!]|$)"
)


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


def _canonical_url(url: str) -> str:
    """Normalize source identity while preserving meaningful query parameters."""
    parts = urlsplit(url.strip())
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_")
            and key.casefold() not in _TRACKING_QUERY_KEYS
        )
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), path, query, "")
    )


def _source_strength_adjustment(url: str) -> float:
    """Return a small deterministic ranking adjustment from obvious URL types."""
    host = (urlsplit(url).hostname or "").casefold()
    if host.endswith(".gov") or ".gov." in host:
        return 0.05
    if host.endswith(".edu") or ".edu." in host or ".ac." in host:
        return 0.03
    if host == "doi.org" or host.endswith(".ncbi.nlm.nih.gov"):
        return 0.03
    if host == "wikipedia.org" or host.endswith(".wikipedia.org"):
        return -0.03
    return 0.0


def _build_evidence(passages: list[RetrievedPassage]) -> list[EvidencePassage]:
    """Deduplicate passages by canonical source and rank unique evidence."""
    strongest_by_url: dict[str, RetrievedPassage] = {}
    for passage in passages:
        canonical_url = _canonical_url(passage.source_url)
        current = strongest_by_url.get(canonical_url)
        if current is None or passage.score > current.score:
            strongest_by_url[canonical_url] = passage

    ranked = sorted(
        strongest_by_url.items(),
        key=lambda item: (
            -(item[1].score + _source_strength_adjustment(item[0])),
            -item[1].score,
            item[0],
        ),
    )
    return [
        EvidencePassage(
            source_id=f"S{index}",
            url=canonical_url,
            text=passage.text,
            score=passage.score,
        )
        for index, (canonical_url, passage) in enumerate(ranked, start=1)
    ]


def _evidence_gap_uncertainty(
    question: str, evidence: list[EvidencePassage]
) -> list[str]:
    """Describe obvious evidence gaps without asking a model to interpret them."""
    if not evidence:
        return ["No relevant evidence was retrieved."]

    signals: list[str] = []
    location_matches = _LOCATION_HINT.findall(question)
    if location_matches:
        location = location_matches[-1]
        if all(location.casefold() not in item.text.casefold() for item in evidence):
            signals.append(
                f"Location mismatch: retrieved evidence does not mention {location}."
            )

    domains = {
        urlsplit(item.url).hostname
        for item in evidence
        if urlsplit(item.url).hostname
    }
    if len(domains) < 2:
        signals.append(
            "Insufficient source diversity: evidence comes from fewer than two domains."
        )

    if max(item.score for item in evidence) < _LOW_CONFIDENCE_SCORE:
        signals.append("Low retrieval confidence: best semantic score is below 0.45.")
    return signals


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
        canonical_url = _canonical_url(hit.url) if hit.url else ""
        if canonical_url and canonical_url not in seen_urls:
            seen_urls.add(canonical_url)
            urls.append(canonical_url)
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

    evidence = _build_evidence(passages)
    uncertainty.extend(_evidence_gap_uncertainty(query, evidence))
    return EvidenceResult(question=query, evidence=evidence, uncertainty=uncertainty)
