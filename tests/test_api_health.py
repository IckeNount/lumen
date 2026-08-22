"""FastAPI health route — baseline smoke test."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
import pytest

from lumen.api.app import create_app
from lumen.pipeline.retrieve import RetrievedPassage
from lumen.pipeline.search import SearchHit


def test_health() -> None:
    app = create_app()
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def _post_stream() -> object:
    return TestClient(create_app()).post(
        "/api/v1/research/stream",
        json={
            "session_id": "deployment-test",
            "question": "What changed?",
            "max_subqueries": 1,
        },
    )


def _stub_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    hits = [
        SearchHit("https://alpha.test", "Alpha study", "alpha"),
        SearchHit("https://beta.test", "Beta study", "beta"),
    ]
    passages = [
        RetrievedPassage("c1", "https://alpha.test", "Alpha evidence", 0.9),
        RetrievedPassage("c2", "https://beta.test", "Beta evidence", 0.8),
    ]
    contradiction = {
        "id": "C1",
        "kind": "direct_conflict",
        "topic": "Outcome",
        "claim_a": {"text": "Alpha wins", "source_ids": ["S1"]},
        "claim_b": {"text": "Beta wins", "source_ids": ["S2"]},
        "explanation": "The sources disagree.",
        "unresolved": None,
    }
    report = (
        "## Key Findings\n\n"
        "- Alpha is better [S1](#source-S1)\n\n"
        "## Report\n\n"
        "# Report heading\n\nAlpha [S1](#source-S1)"
    )

    monkeypatch.setattr("lumen.pipeline.orchestrator.decompose_question", lambda *a, **k: ["alpha"])
    monkeypatch.setattr("lumen.pipeline.orchestrator.search_web", lambda *a, **k: hits)
    monkeypatch.setattr("lumen.pipeline.orchestrator.fetch_url", lambda url: f"text from {url}")
    monkeypatch.setattr(
        "lumen.pipeline.orchestrator.embed_texts",
        lambda texts, **kwargs: [[0.1] for _ in texts],
    )
    monkeypatch.setattr("lumen.pipeline.orchestrator.upsert_chunks", lambda *a, **k: None)
    monkeypatch.setattr("lumen.pipeline.orchestrator.retrieve", lambda *a, **k: passages)
    monkeypatch.setattr("lumen.pipeline.orchestrator.find_contradictions", lambda *a, **k: [contradiction])
    monkeypatch.setattr("lumen.pipeline.orchestrator.iter_synthesize_report", lambda *a, **k: iter([report]))


def test_stream_emits_progress_and_one_structured_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_pipeline(monkeypatch)

    response = _post_stream()
    events = [json.loads(line) for line in response.text.splitlines()]

    assert response.status_code == 200
    assert events[0]["type"] == "run_started"
    assert [event["stage"] for event in events if event["type"] == "stage"] == [
        "planning",
        "planning",
        "searching",
        "searching",
        "reading",
        "reading",
        "comparing",
        "comparing",
        "writing",
        "writing",
    ]
    assert len([event for event in events if event["type"] == "source_found"]) == 2
    assert len([event for event in events if event["type"] in {"done", "error"}]) == 1
    assert events[-1]["type"] == "done"

    result = events[-1]["result"]
    assert result["key_findings"] == [
        {"id": "K1", "text": "Alpha is better", "source_ids": ["S1"]}
    ]
    assert [source["id"] for source in result["sources"]] == ["S1", "S2"]
    assert result["contradictions"][0]["claim_a"]["source_ids"] == ["S1"]
    assert result["contradictions"][0]["claim_b"]["source_ids"] == ["S2"]
    assert "[S1](#source-S1)" in result["report_markdown"]


def test_stream_keeps_partial_results_when_a_source_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_pipeline(monkeypatch)

    def fetch(url: str) -> str:
        if url == "https://beta.test":
            raise RuntimeError("offline")
        return "alpha evidence"

    monkeypatch.setattr("lumen.pipeline.orchestrator.fetch_url", fetch)

    events = [json.loads(line) for line in _post_stream().text.splitlines()]
    reading = [
        event
        for event in events
        if event.get("type") == "stage" and event.get("stage") == "reading"
    ]

    assert reading[-1]["status"] == "warning"
    assert events[-1]["type"] == "done"
    assert events[-1]["result"]["uncertainty_notes"] == [
        "Failed to fetch https://beta.test"
    ]


def test_stream_returns_empty_result_when_no_source_can_be_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_pipeline(monkeypatch)
    monkeypatch.setattr(
        "lumen.pipeline.orchestrator.fetch_url",
        lambda url: (_ for _ in ()).throw(RuntimeError(url)),
    )

    events = [json.loads(line) for line in _post_stream().text.splitlines()]
    result = events[-1]["result"]

    assert events[-1]["type"] == "done"
    assert result["key_findings"] == []
    assert result["contradictions"] == []
    assert result["report_markdown"] == ""
    assert result["sources"] == []
    assert len(result["uncertainty_notes"]) == 3


def test_stream_returns_one_safe_error_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lumen.pipeline.orchestrator.decompose_question",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("secret detail")),
    )

    events = [json.loads(line) for line in _post_stream().text.splitlines()]

    assert len([event for event in events if event["type"] in {"done", "error"}]) == 1
    assert events[-1] == {
        "type": "error",
        "stage": "planning",
        "message": "Research failed during this stage.",
        "recoverable": True,
    }
