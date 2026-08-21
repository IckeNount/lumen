"""Model-free evidence retrieval with local semantic embeddings."""

from __future__ import annotations

from pathlib import Path

from lumen.config import Settings
from lumen.pipeline.evidence import research_evidence
from lumen.pipeline.retrieve import RetrievedPassage
from lumen.pipeline.search import SearchHit


def test_research_evidence_ranks_relevant_source(monkeypatch, tmp_path: Path) -> None:
    photosynthesis_url = "https://plants.example.test/photosynthesis"
    unrelated_url = "https://history.example.test/roman-roads"
    hits = [
        SearchHit(
            url=photosynthesis_url,
            title="Photosynthesis",
            snippet="How plants convert sunlight into stored chemical energy.",
        ),
        SearchHit(
            url=unrelated_url,
            title="Roman roads",
            snippet="Construction techniques used in ancient transport networks.",
        ),
    ]
    documents = {
        photosynthesis_url: (
            "Photosynthesis lets green plants use chlorophyll to capture sunlight. "
            "They convert carbon dioxide and water into glucose, storing solar energy "
            "as chemical energy while releasing oxygen."
        ),
        unrelated_url: (
            "Roman engineers built durable roads from layered stone and gravel. "
            "The road network moved soldiers, traders, and messages across the empire."
        ),
    }

    monkeypatch.setattr(
        "lumen.pipeline.evidence.search_web",
        lambda query, *, max_results, settings: hits[:max_results],
    )
    monkeypatch.setattr("lumen.pipeline.evidence.fetch_url", documents.__getitem__)

    settings = Settings.model_construct(
        chroma_persist_directory=str(tmp_path / "chroma"),
        chroma_collection_prefix="test_evidence",
        lumen_max_retrieval_chunks=4,
    )
    result = research_evidence(
        "How do plants store energy from sunlight?",
        session_id="semantic-ranking",
        max_sources=2,
        settings=settings,
    )

    assert result.question == "How do plants store energy from sunlight?"
    assert len(result.evidence) == 2
    assert result.evidence[0].source_id == "S1"
    assert result.evidence[0].url == photosynthesis_url
    assert "glucose" in result.evidence[0].text
    assert result.evidence[0].score >= result.evidence[1].score
    assert result.uncertainty == []


def test_research_evidence_deduplicates_and_prefers_stronger_sources(
    monkeypatch, tmp_path: Path
) -> None:
    hits = [
        SearchHit(url="https://en.wikipedia.org/wiki/Kpod", title="Kpod", snippet=""),
        SearchHit(url="https://www.hsa.gov.sg/alerts/kpod", title="Alert", snippet=""),
    ]
    passages = [
        RetrievedPassage(
            chunk_id="wiki-1",
            source_url="https://en.wikipedia.org/wiki/Kpod?utm_source=test#Deaths",
            text="A reference passage with a slightly higher semantic score.",
            score=0.62,
        ),
        RetrievedPassage(
            chunk_id="official-1",
            source_url="https://www.hsa.gov.sg/alerts/kpod",
            text="An official health authority alert.",
            score=0.60,
        ),
        RetrievedPassage(
            chunk_id="wiki-2",
            source_url="https://en.wikipedia.org/wiki/Kpod#Background",
            text="A second chunk from the same reference source.",
            score=0.59,
        ),
    ]
    monkeypatch.setattr(
        "lumen.pipeline.evidence.search_web",
        lambda query, *, max_results, settings: hits,
    )
    monkeypatch.setattr("lumen.pipeline.evidence.fetch_url", lambda url: "seed text")
    monkeypatch.setattr(
        "lumen.pipeline.evidence.embed_texts_locally",
        lambda texts: [[0.0] for _ in texts],
    )
    monkeypatch.setattr("lumen.pipeline.evidence.upsert_chunks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "lumen.pipeline.evidence.retrieve", lambda *args, **kwargs: passages
    )

    settings = Settings.model_construct(
        chroma_persist_directory=str(tmp_path / "chroma"),
        chroma_collection_prefix="test_evidence",
        lumen_max_retrieval_chunks=4,
    )
    result = research_evidence("What is in a Kpod?", settings=settings)

    assert [item.url for item in result.evidence] == [
        "https://www.hsa.gov.sg/alerts/kpod",
        "https://en.wikipedia.org/wiki/Kpod",
    ]
    assert [item.source_id for item in result.evidence] == ["S1", "S2"]
    assert result.evidence[1].score == 0.62


def test_research_evidence_reports_obvious_evidence_gaps(
    monkeypatch, tmp_path: Path
) -> None:
    hit = SearchHit(url="https://example.test/report", title="Report", snippet="")
    passage = RetrievedPassage(
        chunk_id="report-1",
        source_url=hit.url,
        text="The reported deaths occurred in Hong Kong.",
        score=0.20,
    )
    monkeypatch.setattr(
        "lumen.pipeline.evidence.search_web",
        lambda query, *, max_results, settings: [hit],
    )
    monkeypatch.setattr("lumen.pipeline.evidence.fetch_url", lambda url: "seed text")
    monkeypatch.setattr(
        "lumen.pipeline.evidence.embed_texts_locally",
        lambda texts: [[0.0] for _ in texts],
    )
    monkeypatch.setattr("lumen.pipeline.evidence.upsert_chunks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "lumen.pipeline.evidence.retrieve", lambda *args, **kwargs: [passage]
    )

    settings = Settings.model_construct(
        chroma_persist_directory=str(tmp_path / "chroma"),
        chroma_collection_prefix="test_evidence",
        lumen_max_retrieval_chunks=4,
    )
    result = research_evidence(
        "What happened to young people in Singapore?", settings=settings
    )

    assert result.uncertainty == [
        "Location mismatch: retrieved evidence does not mention Singapore.",
        "Insufficient source diversity: evidence comes from fewer than two domains.",
        "Low retrieval confidence: best semantic score is below 0.45.",
    ]
