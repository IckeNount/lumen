"""Model-free evidence retrieval with local semantic embeddings."""

from __future__ import annotations

from pathlib import Path

from lumen.config import Settings
from lumen.pipeline.evidence import research_evidence
from lumen.pipeline.search import SearchHit


def test_research_evidence_ranks_relevant_source(monkeypatch, tmp_path: Path) -> None:
    photosynthesis_url = "https://example.test/photosynthesis"
    unrelated_url = "https://example.test/roman-roads"
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
